#ifndef AI_NOTEBOOK_FAST_VOCAB_SERVICE_H
#define AI_NOTEBOOK_FAST_VOCAB_SERVICE_H

#include <optional>
#include <sqlite3.h>
#include <string>
#include <vector>

/**
 * Fast path bilingual vocab service implemented in C++.
 *
 * Responsibilities:
 *  - Ensure the SQLite schema exists (terms/synonym_edge/translation_edge/user_vocab).
 *  - Load optional SQL dump on first use.
 *  - Record a bilingual vocab item (english/chinese + optional meanings) and link it.
 *  - Search recorded vocab and base tables using a light-weight similarity (bigram Dice).
 *
 * This is designed to be called from a small CLI in fast_vocab_service.cpp, but
 * the class can also be embedded in other executables.
 */
class FastVocabService {
  public:
    struct VocabEntry {
        int id = 0;
        std::string english;
        std::string chinese;
        std::string meaning_en;
        std::string meaning_zh;
        bool deleted = false;
    };

    struct SearchHit {
        double score = 0.0;
        std::string source;      // "user", "translation_edge", "synonym_edge"
        std::string english;
        std::string chinese;
        std::string extra;       // free-form details (e.g., meaning or edge kind)
    };

    explicit FastVocabService(const std::string &db_path);
    ~FastVocabService();

    // Create/open the DB; if sql_dump is provided and the DB was missing, load it.
    void initialize(const std::optional<std::string> &sql_dump_path, bool rebuild);

    // Add or update a vocab entry; returns row id.
    int record(const std::optional<std::string> &english,
               const std::optional<std::string> &chinese,
               const std::optional<std::string> &meaning_en,
               const std::optional<std::string> &meaning_zh);

    bool soft_delete(int id);
    bool restore_entry(int id);
    bool update_entry(int id,
                      const std::optional<std::string> &english,
                      const std::optional<std::string> &chinese,
                      const std::optional<std::string> &meaning_en,
                      const std::optional<std::string> &meaning_zh);

    // Expose snapshots for interactive menus.
    std::vector<VocabEntry> list_active();
    std::vector<VocabEntry> list_deleted();
    std::optional<VocabEntry> get_entry(int id);

    // Search user vocab (and optionally base tables) with a bigram Dice similarity.
    std::vector<SearchHit> search(const std::string &query,
                                  const std::string &language_hint,
                                  int topk,
                                  bool include_base);

  private:
    sqlite3 *db_ = nullptr;
    std::string db_path_;

    void ensure_schema();
    void load_sql_dump(const std::string &sql_path);
    void ensure_term(const std::string &term, const std::string &lang);
    void upsert_translation_edge(const std::string &en_term, const std::string &zh_term, double score);

    std::vector<VocabEntry> load_user_vocab();
    std::vector<VocabEntry> load_deleted_vocab();
    std::optional<VocabEntry> fetch_entry(int id);
    std::vector<SearchHit> search_user_vocab(const std::string &query, const std::string &lang, int topk);
    std::vector<SearchHit> search_base_tables(const std::string &query, const std::string &lang, int topk);

    // Helpers
    static std::string trim(const std::string &s);
    static std::string to_lower_ascii(const std::string &s);
    static bool is_cjk_heuristic(const std::string &s);
    static std::vector<std::string> bigrams(const std::string &s);
    static double dice_score(const std::vector<std::string> &a, const std::vector<std::string> &b);
};

#endif // AI_NOTEBOOK_FAST_VOCAB_SERVICE_H
