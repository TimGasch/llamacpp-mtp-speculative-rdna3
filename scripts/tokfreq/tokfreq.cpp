// tokfreq — count token frequencies of text files with a model's tokenizer (vocab-only load, CPU).
// Used to pick the reduced draft vocabulary for the MTP draft head (iteration 3).
// Usage: tokfreq <model.gguf> <out.csv> <file1> [file2 ...]
// Output CSV: token_id,count,is_control
#include "llama.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

int main(int argc, char ** argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: tokfreq <model.gguf> <out.csv> <files...>\n");
        return 2;
    }
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.vocab_only = true;
    llama_model * model = llama_model_load_from_file(argv[1], mp);
    if (!model) { fprintf(stderr, "load failed\n"); return 1; }
    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int n_vocab = llama_vocab_n_tokens(vocab);
    std::vector<long long> counts(n_vocab, 0);
    long long total = 0;
    for (int fi = 3; fi < argc; fi++) {
        std::ifstream f(argv[fi], std::ios::binary);
        std::stringstream ss; ss << f.rdbuf();
        const std::string text = ss.str();
        // tokenize in ~64 KB chunks cut at newlines (keeps memory bounded)
        size_t pos = 0;
        while (pos < text.size()) {
            size_t end = std::min(text.size(), pos + 65536);
            if (end < text.size()) {
                const size_t nl = text.rfind('\n', end);
                if (nl != std::string::npos && nl > pos) end = nl + 1;
            }
            const std::string chunk = text.substr(pos, end - pos);
            std::vector<llama_token> toks(chunk.size() + 16);
            int n = llama_tokenize(vocab, chunk.c_str(), (int) chunk.size(), toks.data(), (int) toks.size(), false, false);
            if (n < 0) { toks.resize(-n); n = llama_tokenize(vocab, chunk.c_str(), (int) chunk.size(), toks.data(), (int) toks.size(), false, false); }
            for (int i = 0; i < n; i++) { counts[toks[i]]++; total++; }
            pos = end;
        }
        fprintf(stderr, "tokfreq: %s done (total tokens so far %lld)\n", argv[fi], total);
    }
    FILE * out = fopen(argv[2], "w");
    fprintf(out, "token_id,count,is_control\n");
    for (int t = 0; t < n_vocab; t++) {
        const bool ctrl = llama_vocab_is_control(vocab, t) || llama_vocab_is_eog(vocab, t);
        fprintf(out, "%d,%lld,%d\n", t, counts[t], ctrl ? 1 : 0);
    }
    fclose(out);
    llama_model_free(model);
    return 0;
}
