#include "common.h"
#include "llama.h"

#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

struct segment {
    std::string id;
    int n_prefix = 0;
    std::vector<llama_token> tokens;
};

static std::string json_escape(const std::string & s) {
    std::string o;
    for (char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += c; }
        else if ((unsigned char) c < 0x20) { char b[8]; snprintf(b, sizeof(b), "\\u%04x", c); o += b; }
        else o += c;
    }
    return o;
}

int main(int argc, char ** argv) {
    std::string segs_path, out_prefix;
    int ub = 1;
    int split = -1;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--") { split = i; break; }
        if (a == "--segs" && i + 1 < argc) { segs_path = argv[++i]; }
        else if (a == "--ub" && i + 1 < argc) { ub = std::stoi(argv[++i]); }
        else if (a == "--out" && i + 1 < argc) { out_prefix = argv[++i]; }
        else { fprintf(stderr, "qdump: unknown argument %s\n", a.c_str()); return 2; }
    }
    if (segs_path.empty() || out_prefix.empty() || split < 0 || ub < 1) {
        fprintf(stderr, "usage: qdump --segs F --ub U --out PREFIX -- <llama args>\n");
        return 2;
    }

    // llama.cpp args: argv[0] + everything after "--"
    std::vector<char *> largv;
    largv.push_back(argv[0]);
    for (int i = split + 1; i < argc; i++) largv.push_back(argv[i]);
    common_params params;
    if (!common_params_parse((int) largv.size(), largv.data(), params, LLAMA_EXAMPLE_SERVER)) {
        return 2;
    }

    // read segments
    std::vector<segment> segs;
    {
        std::ifstream f(segs_path);
        std::string line;
        while (std::getline(f, line)) {
            if (line.empty()) continue;
            std::istringstream ss(line);
            segment s;
            ss >> s.id >> s.n_prefix;
            long long t;
            while (ss >> t) s.tokens.push_back((llama_token) t);
            if (s.n_prefix < 1 || (int) s.tokens.size() < s.n_prefix + 2) {
                fprintf(stderr, "qdump: bad segment %s\n", s.id.c_str());
                return 2;
            }
            segs.push_back(std::move(s));
        }
    }

    llama_backend_init();
    llama_numa_init(params.numa);
    auto init = common_init_from_params(params);
    llama_model * model = init->model();
    llama_context * ctx = init->context();
    if (!model || !ctx) { fprintf(stderr, "qdump: failed to init model/context\n"); return 1; }

    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int n_vocab = llama_vocab_n_tokens(vocab);
    const int n_batch = (int) llama_n_batch(ctx);
    if (ub > (int) llama_n_ubatch(ctx)) {
        fprintf(stderr, "qdump: --ub %d exceeds n_ubatch %u\n", ub, llama_n_ubatch(ctx));
        return 2;
    }

    FILE * fl = fopen((out_prefix + ".logits").c_str(), "wb");
    if (!fl) { fprintf(stderr, "qdump: cannot open output\n"); return 1; }

    llama_batch batch = llama_batch_init(std::max(n_batch, ub), 0, 1);
    llama_memory_t mem = llama_get_memory(ctx);

    std::ostringstream seg_json;
    double t_scored_ms = 0.0;
    long long n_scored_total = 0;
    for (size_t si = 0; si < segs.size(); si++) {
        const segment & s = segs[si];
        llama_memory_clear(mem, true);
        const int N = (int) s.tokens.size();
        // prompt prefix
        for (int p = 0; p < s.n_prefix; p += n_batch) {
            common_batch_clear(batch);
            for (int i = p; i < std::min(p + n_batch, s.n_prefix); i++) {
                common_batch_add(batch, s.tokens[i], i, { 0 }, false);
            }
            if (llama_decode(ctx, batch) != 0) { fprintf(stderr, "qdump: decode failed (prefix)\n"); return 1; }
        }
        // scored inputs
        auto t0 = std::chrono::steady_clock::now();
        for (int p = s.n_prefix; p < N - 1; p += ub) {
            const int e = std::min(p + ub, N - 1);
            common_batch_clear(batch);
            for (int i = p; i < e; i++) {
                common_batch_add(batch, s.tokens[i], i, { 0 }, true);
            }
            if (llama_decode(ctx, batch) != 0) { fprintf(stderr, "qdump: decode failed (scored)\n"); return 1; }
            for (int j = 0; j < e - p; j++) {
                const float * lg = llama_get_logits_ith(ctx, j);
                fwrite(lg, sizeof(float), n_vocab, fl);
            }
        }
        t_scored_ms += std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        const int n_scored = N - 1 - s.n_prefix;
        n_scored_total += n_scored;
        seg_json << (si ? ",\n" : "\n") << "  {\"id\": \"" << json_escape(s.id) << "\", \"n_tokens\": " << N
                 << ", \"n_prefix\": " << s.n_prefix << ", \"n_scored\": " << n_scored << ", \"targets\": [";
        for (int i = s.n_prefix + 1; i < N; i++) seg_json << (i > s.n_prefix + 1 ? "," : "") << s.tokens[i];
        seg_json << "]}";
        fprintf(stderr, "qdump: segment %s done (%d scored)\n", s.id.c_str(), n_scored);
    }
    fclose(fl);
    llama_batch_free(batch);

    std::ofstream fj(out_prefix + ".json");
    fj << "{\n \"tool\": \"qdump\",\n \"ub\": " << ub << ",\n \"n_vocab\": " << n_vocab
       << ",\n \"n_ctx\": " << llama_n_ctx(ctx) << ",\n \"n_batch\": " << n_batch
       << ",\n \"n_ubatch\": " << llama_n_ubatch(ctx) << ",\n \"n_scored_total\": " << n_scored_total
       << ",\n \"t_scored_ms\": " << t_scored_ms << ",\n \"llama_args\": [";
    for (size_t i = 1; i < largv.size(); i++) fj << (i > 1 ? ", " : "") << "\"" << json_escape(largv[i]) << "\"";
    fj << "],\n \"system_info\": \"" << json_escape(llama_print_system_info()) << "\",\n \"segments\": [" << seg_json.str() << "\n ]\n}\n";
    fprintf(stderr, "qdump: wrote %lld positions x %d vocab\n", n_scored_total, n_vocab);
    return 0;
}
