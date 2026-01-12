#include "..\\header-files-new\\fast_vocab_service.h"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using std::optional;
using std::string;
using std::vector;

namespace {

int exec_sql(sqlite3 *db, const string &sql) {
    char *errmsg = nullptr;
    int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, &errmsg);
    if (rc != SQLITE_OK) {
        std::cerr << "SQL error: " << (errmsg ? errmsg : "unknown") << "\n";
        if (errmsg) sqlite3_free(errmsg);
    }
    return rc;
}

string trim_local(const string &s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) start++;
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) end--;
    return s.substr(start, end - start);
}

string joined_fields(const FastVocabService::VocabEntry &e) {
    std::ostringstream oss;
    if (!e.english.empty()) oss << e.english << " ";
    if (!e.chinese.empty()) oss << e.chinese << " ";
    if (!e.meaning_en.empty()) oss << e.meaning_en << " ";
    if (!e.meaning_zh.empty()) oss << e.meaning_zh;
    return trim_local(oss.str());
}

} // namespace

FastVocabService::FastVocabService(const string &db_path) : db_path_(db_path) {}

FastVocabService::~FastVocabService() {
    if (db_) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

void FastVocabService::initialize(const optional<string> &sql_dump_path, bool rebuild) {
    const bool existed = [] (const string &p) { std::ifstream f(p); return f.good(); }(db_path_);
    if (rebuild && existed) {
        std::remove(db_path_.c_str());
    }
    if (sqlite3_open(db_path_.c_str(), &db_) != SQLITE_OK) {
        throw std::runtime_error("Failed to open DB at " + db_path_);
    }
    ensure_schema();
    if (sql_dump_path && (!existed || rebuild)) {
        load_sql_dump(*sql_dump_path);
    }
    ensure_schema(); // in case dump lacked tables
}

void FastVocabService::ensure_schema() {
    const char *schema_sql =
        R"SQL(
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS terms(
            term TEXT PRIMARY KEY,
            language TEXT
        );
        CREATE TABLE IF NOT EXISTS synonym_edge(
            id INTEGER PRIMARY KEY,
            left_term TEXT,
            right_term TEXT,
            language TEXT,
            score REAL,
            source TEXT,
            UNIQUE(left_term, right_term, language, source)
        );
        CREATE TABLE IF NOT EXISTS translation_edge(
            id INTEGER PRIMARY KEY,
            en_term TEXT,
            zh_term TEXT,
            score REAL,
            source TEXT,
            UNIQUE(en_term, zh_term, source)
        );
        CREATE TABLE IF NOT EXISTS user_vocab(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english TEXT,
            chinese TEXT,
            meaning_en TEXT,
            meaning_zh TEXT,
            deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(english, chinese)
        );
        CREATE TRIGGER IF NOT EXISTS trg_user_vocab_updated
        AFTER UPDATE ON user_vocab
        FOR EACH ROW
        BEGIN
            UPDATE user_vocab SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        CREATE INDEX IF NOT EXISTS idx_user_vocab_en ON user_vocab(english);
        CREATE INDEX IF NOT EXISTS idx_user_vocab_zh ON user_vocab(chinese);
        )SQL";
    exec_sql(db_, schema_sql);
    // Add deleted column if missing (suppress duplicate errors)
    sqlite3_stmt *stmt = nullptr;
    bool has_deleted = false;
    if (sqlite3_prepare_v2(db_, "PRAGMA table_info(user_vocab);", -1, &stmt, nullptr) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            const unsigned char *name = sqlite3_column_text(stmt, 1);
            if (name && std::string(reinterpret_cast<const char *>(name)) == "deleted") {
                has_deleted = true;
                break;
            }
        }
    }
    sqlite3_finalize(stmt);
    if (!has_deleted) {
        exec_sql(db_, "ALTER TABLE user_vocab ADD COLUMN deleted INTEGER DEFAULT 0;");
    }
}

void FastVocabService::load_sql_dump(const string &sql_path) {
    std::ifstream fin(sql_path);
    if (!fin.is_open()) {
        throw std::runtime_error("Failed to open SQL dump: " + sql_path);
    }
    std::ostringstream buffer;
    buffer << fin.rdbuf();
    exec_sql(db_, buffer.str());
}

void FastVocabService::ensure_term(const string &term, const string &lang) {
    static const char *SQL = "INSERT OR IGNORE INTO terms(term, language) VALUES (?, ?);";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return;
    sqlite3_bind_text(stmt, 1, term.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, lang.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void FastVocabService::upsert_translation_edge(const string &en_term, const string &zh_term, double score) {
    static const char *SQL =
        "INSERT OR REPLACE INTO translation_edge(en_term, zh_term, score, source) VALUES (?, ?, ?, 'user');";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return;
    sqlite3_bind_text(stmt, 1, en_term.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, zh_term.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(stmt, 3, score);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

int FastVocabService::record(const optional<string> &english,
                             const optional<string> &chinese,
                             const optional<string> &meaning_en,
                             const optional<string> &meaning_zh) {
    const string en_norm = english ? to_lower_ascii(trim(*english)) : "";
    const string zh_norm = chinese ? trim(*chinese) : "";
    const string mean_en = meaning_en ? trim(*meaning_en) : "";
    const string mean_zh = meaning_zh ? trim(*meaning_zh) : "";
    if (en_norm.empty() && zh_norm.empty()) {
        throw std::invalid_argument("Provide at least one of English/Chinese");
    }

    static const char *SQL =
        R"SQL(
        INSERT INTO user_vocab(english, chinese, meaning_en, meaning_zh)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(english, chinese) DO UPDATE SET
            meaning_en = excluded.meaning_en,
            meaning_zh = excluded.meaning_zh,
            updated_at = CURRENT_TIMESTAMP;
        )SQL";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare insert into user_vocab");
    }
    sqlite3_bind_text(stmt, 1, en_norm.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, zh_norm.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, mean_en.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, mean_zh.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    // Fetch id (works for insert or conflict update)
    int row_id = 0;
    sqlite3_stmt *sel = nullptr;
    if (sqlite3_prepare_v2(db_, "SELECT id FROM user_vocab WHERE english=? AND chinese=? LIMIT 1;", -1, &sel, nullptr) ==
        SQLITE_OK) {
        sqlite3_bind_text(sel, 1, en_norm.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(sel, 2, zh_norm.c_str(), -1, SQLITE_TRANSIENT);
        if (sqlite3_step(sel) == SQLITE_ROW) {
            row_id = sqlite3_column_int(sel, 0);
        }
    }
    sqlite3_finalize(sel);

    if (!en_norm.empty()) ensure_term(en_norm, "en");
    if (!zh_norm.empty()) ensure_term(zh_norm, "zh");
    if (!en_norm.empty() && !zh_norm.empty()) {
        // Simple score: perfect bilingual pair -> 1.0
        upsert_translation_edge(en_norm, zh_norm, 1.0);
    }
    return row_id;
}

vector<FastVocabService::VocabEntry> FastVocabService::load_user_vocab() {
    vector<VocabEntry> out;
    static const char *SQL = "SELECT id, english, chinese, meaning_en, meaning_zh, deleted FROM user_vocab WHERE deleted = 0;";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return out;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        VocabEntry e;
        e.id = sqlite3_column_int(stmt, 0);
        e.english = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1) ? sqlite3_column_text(stmt, 1) : (const unsigned char*)"");
        e.chinese = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 2) ? sqlite3_column_text(stmt, 2) : (const unsigned char*)"");
        e.meaning_en = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 3) ? sqlite3_column_text(stmt, 3) : (const unsigned char*)"");
        e.meaning_zh = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 4) ? sqlite3_column_text(stmt, 4) : (const unsigned char*)"");
        e.deleted = sqlite3_column_int(stmt, 5) != 0;
        out.push_back(std::move(e));
    }
    sqlite3_finalize(stmt);
    return out;
}

vector<FastVocabService::VocabEntry> FastVocabService::load_deleted_vocab() {
    vector<VocabEntry> out;
    static const char *SQL = "SELECT id, english, chinese, meaning_en, meaning_zh, deleted FROM user_vocab WHERE deleted != 0;";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return out;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        VocabEntry e;
        e.id = sqlite3_column_int(stmt, 0);
        e.english = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1) ? sqlite3_column_text(stmt, 1) : (const unsigned char*)"");
        e.chinese = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 2) ? sqlite3_column_text(stmt, 2) : (const unsigned char*)"");
        e.meaning_en = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 3) ? sqlite3_column_text(stmt, 3) : (const unsigned char*)"");
        e.meaning_zh = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 4) ? sqlite3_column_text(stmt, 4) : (const unsigned char*)"");
        e.deleted = sqlite3_column_int(stmt, 5) != 0;
        out.push_back(std::move(e));
    }
    sqlite3_finalize(stmt);
    return out;
}

std::optional<FastVocabService::VocabEntry> FastVocabService::fetch_entry(int id) {
    static const char *SQL = "SELECT id, english, chinese, meaning_en, meaning_zh, deleted FROM user_vocab WHERE id = ?;";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return std::nullopt;
    sqlite3_bind_int(stmt, 1, id);
    std::optional<VocabEntry> res;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        VocabEntry e;
        e.id = sqlite3_column_int(stmt, 0);
        e.english = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1) ? sqlite3_column_text(stmt, 1) : (const unsigned char*)"");
        e.chinese = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 2) ? sqlite3_column_text(stmt, 2) : (const unsigned char*)"");
        e.meaning_en = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 3) ? sqlite3_column_text(stmt, 3) : (const unsigned char*)"");
        e.meaning_zh = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 4) ? sqlite3_column_text(stmt, 4) : (const unsigned char*)"");
        e.deleted = sqlite3_column_int(stmt, 5) != 0;
        res = e;
    }
    sqlite3_finalize(stmt);
    return res;
}

std::vector<FastVocabService::VocabEntry> FastVocabService::list_active() {
    return load_user_vocab();
}

std::vector<FastVocabService::VocabEntry> FastVocabService::list_deleted() {
    return load_deleted_vocab();
}

std::optional<FastVocabService::VocabEntry> FastVocabService::get_entry(int id) {
    return fetch_entry(id);
}

bool FastVocabService::soft_delete(int id) {
    static const char *SQL = "UPDATE user_vocab SET deleted = 1 WHERE id = ?;";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return false;
    sqlite3_bind_int(stmt, 1, id);
    bool ok = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return ok;
}

bool FastVocabService::restore_entry(int id) {
    static const char *SQL = "UPDATE user_vocab SET deleted = 0 WHERE id = ?;";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return false;
    sqlite3_bind_int(stmt, 1, id);
    bool ok = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    return ok;
}

bool FastVocabService::update_entry(int id,
                                    const optional<string> &english,
                                    const optional<string> &chinese,
                                    const optional<string> &meaning_en,
                                    const optional<string> &meaning_zh) {
    auto existing = fetch_entry(id);
    if (!existing) return false;
    const string en_norm = english ? to_lower_ascii(trim(*english)) : existing->english;
    const string zh_norm = chinese ? trim(*chinese) : existing->chinese;
    const string mean_en = meaning_en ? trim(*meaning_en) : existing->meaning_en;
    const string mean_zh = meaning_zh ? trim(*meaning_zh) : existing->meaning_zh;

    static const char *SQL =
        "UPDATE user_vocab SET english=?, chinese=?, meaning_en=?, meaning_zh=?, updated_at=CURRENT_TIMESTAMP WHERE id=?";
    sqlite3_stmt *stmt = nullptr;
    if (sqlite3_prepare_v2(db_, SQL, -1, &stmt, nullptr) != SQLITE_OK) return false;
    sqlite3_bind_text(stmt, 1, en_norm.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, zh_norm.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, mean_en.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, mean_zh.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 5, id);
    bool ok = sqlite3_step(stmt) == SQLITE_DONE;
    sqlite3_finalize(stmt);
    if (ok) {
        if (!en_norm.empty()) ensure_term(en_norm, "en");
        if (!zh_norm.empty()) ensure_term(zh_norm, "zh");
    }
    return ok;
}

vector<FastVocabService::SearchHit> FastVocabService::search_user_vocab(const string &query, const string &lang, int topk) {
    vector<SearchHit> hits;
    const string q_norm = (lang == "en") ? to_lower_ascii(trim(query)) : trim(query);
    const auto q_bi = bigrams(q_norm);
    auto entries = load_user_vocab();
    for (const auto &entry : entries) {
        double best = 0.0;
        auto consider = [&](const string &text) {
            if (text.empty()) return;
            double s = dice_score(q_bi, bigrams(text));
            if (s > best) best = s;
        };
        if (lang == "en") {
            consider(entry.english);
            consider(entry.meaning_en);
            consider(entry.chinese);
            consider(entry.meaning_zh);
        } else if (lang == "zh") {
            consider(entry.chinese);
            consider(entry.meaning_zh);
            consider(entry.english);
            consider(entry.meaning_en);
        } else { // both/auto fallback
            consider(joined_fields(entry));
        }
        if (best > 0.0) {
            hits.push_back({best, "user", entry.english, entry.chinese, ""});
        }
    }
    std::sort(hits.begin(), hits.end(), [](const SearchHit &a, const SearchHit &b) { return a.score > b.score; });
    if (static_cast<int>(hits.size()) > topk) hits.resize(topk);
    return hits;
}

vector<FastVocabService::SearchHit> FastVocabService::search_base_tables(const string &query, const string &lang, int topk) {
    vector<SearchHit> hits;
    const string pattern = "%" + query + "%";

    // Translation edges
    const char *sql_trans_en =
        "SELECT en_term, zh_term, score FROM translation_edge WHERE en_term LIKE ? ORDER BY score DESC LIMIT ?";
    const char *sql_trans_zh =
        "SELECT en_term, zh_term, score FROM translation_edge WHERE zh_term LIKE ? ORDER BY score DESC LIMIT ?";
    sqlite3_stmt *stmt = nullptr;
        if (lang == "en" || lang == "both") {
            if (sqlite3_prepare_v2(db_, sql_trans_en, -1, &stmt, nullptr) == SQLITE_OK) {
                sqlite3_bind_text(stmt, 1, pattern.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(stmt, 2, topk);
                while (sqlite3_step(stmt) == SQLITE_ROW) {
                    string en = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 0));
                string zh = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1));
                double score = sqlite3_column_double(stmt, 2);
                hits.push_back({score, "translation_edge", en, zh, ""});
            }
        }
        sqlite3_finalize(stmt);
    }
    if (lang == "zh" || lang == "both") {
        if (sqlite3_prepare_v2(db_, sql_trans_zh, -1, &stmt, nullptr) == SQLITE_OK) {
            sqlite3_bind_text(stmt, 1, pattern.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int(stmt, 2, topk);
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                string en = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 0));
                string zh = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1));
                double score = sqlite3_column_double(stmt, 2);
                hits.push_back({score, "translation_edge", en, zh, ""});
            }
        }
        sqlite3_finalize(stmt);
    }

    // Synonym edges (language-specific)
    const char *sql_syn =
        "SELECT left_term, right_term, score FROM synonym_edge WHERE language = ? AND (left_term LIKE ? OR right_term LIKE ?) ORDER BY score DESC LIMIT ?";
    if (lang == "en" || lang == "both" || lang == "zh") {
        string lang_code = (lang == "both") ? "en" : lang;
        if (sqlite3_prepare_v2(db_, sql_syn, -1, &stmt, nullptr) == SQLITE_OK) {
            sqlite3_bind_text(stmt, 1, lang_code.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(stmt, 2, pattern.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(stmt, 3, pattern.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int(stmt, 4, topk);
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                string left = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 0));
                string right = reinterpret_cast<const char *>(sqlite3_column_text(stmt, 1));
                double score = sqlite3_column_double(stmt, 2);
                // For same-language synonyms, mark the language in extra to avoid mislabeling as ZH.
                hits.push_back({score, "synonym_edge", left, right, "lang=" + lang_code});
            }
        }
        sqlite3_finalize(stmt);
    }

    std::sort(hits.begin(), hits.end(), [](const SearchHit &a, const SearchHit &b) { return a.score > b.score; });
    if (static_cast<int>(hits.size()) > topk) hits.resize(topk);
    return hits;
}

vector<FastVocabService::SearchHit> FastVocabService::search(const string &query,
                                                             const string &language_hint,
                                                             int topk,
                                                             bool include_base) {
    string lang = language_hint;
    if (lang == "auto") {
        lang = is_cjk_heuristic(query) ? "zh" : "en";
    }
    auto user_hits = search_user_vocab(query, lang, topk);
    if (!include_base) {
        return user_hits;
    }
    auto base_hits = search_base_tables(query, (lang == "auto") ? "both" : lang, topk);
    user_hits.insert(user_hits.end(), base_hits.begin(), base_hits.end());
    std::sort(user_hits.begin(), user_hits.end(), [](const SearchHit &a, const SearchHit &b) { return a.score > b.score; });
    if (static_cast<int>(user_hits.size()) > topk) user_hits.resize(topk);
    return user_hits;
}

// ---- helpers ----------------------------------------------------------

string FastVocabService::trim(const string &s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) start++;
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) end--;
    return s.substr(start, end - start);
}

string FastVocabService::to_lower_ascii(const string &s) {
    string out = s;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return out;
}

bool FastVocabService::is_cjk_heuristic(const string &s) {
    for (unsigned char c : s) {
        if (c >= 0xE4) return true; // crude heuristic for UTF-8 Chinese bytes
    }
    return false;
}

vector<string> FastVocabService::bigrams(const string &s) {
    vector<string> grams;
    if (s.size() < 2) {
        if (!s.empty()) grams.push_back(s);
        return grams;
    }
    for (size_t i = 0; i + 1 < s.size(); ++i) {
        grams.push_back(s.substr(i, 2));
    }
    return grams;
}

double FastVocabService::dice_score(const vector<string> &a, const vector<string> &b) {
    if (a.empty() || b.empty()) return 0.0;
    std::unordered_map<string, int> freq;
    for (const auto &g : a) freq[g]++;
    int overlap = 0;
    for (const auto &g : b) {
        auto it = freq.find(g);
        if (it != freq.end() && it->second > 0) {
            overlap++;
            it->second--;
        }
    }
    const double denom = static_cast<double>(a.size() + b.size());
    return denom == 0.0 ? 0.0 : (2.0 * overlap) / denom;
}

// ---- CLI --------------------------------------------------------------

struct CliOptions {
    string cmd;
    string db = "notebook.db";
    optional<string> sql_dump;
    bool rebuild = false;

    optional<string> english;
    optional<string> chinese;
    optional<string> meaning_en;
    optional<string> meaning_zh;

    string query;
    string language = "auto";
    int topk = 10;
    bool include_base = false;
};

void print_usage() {
    std::cout << "fast_vocab_service CLI\n"
              << "Commands:\n"
              << "  init   --db <path> [--sql-dump <file>] [--rebuild]\n"
              << "  record --db <path> [--english <text>] [--chinese <text>] [--meaning-en <text>] [--meaning-zh <text>]\n"
              << "  search --db <path> --query <text> [--language auto|en|zh|both] [--topk N] [--include-base]\n";
}

optional<string> next_value(int &i, int argc, char **argv) {
    if (i + 1 >= argc) return std::nullopt;
    return string(argv[++i]);
}

bool parse_args(int argc, char **argv, CliOptions &opts) {
    if (argc < 2) return false;
    opts.cmd = argv[1];
    for (int i = 2; i < argc; ++i) {
        string arg = argv[i];
        if (arg == "--db") {
            auto v = next_value(i, argc, argv);
            if (v) opts.db = *v;
        } else if (arg == "--sql-dump") {
            opts.sql_dump = next_value(i, argc, argv);
        } else if (arg == "--rebuild") {
            opts.rebuild = true;
        } else if (arg == "--english") {
            opts.english = next_value(i, argc, argv);
        } else if (arg == "--chinese") {
            opts.chinese = next_value(i, argc, argv);
        } else if (arg == "--meaning-en") {
            opts.meaning_en = next_value(i, argc, argv);
        } else if (arg == "--meaning-zh") {
            opts.meaning_zh = next_value(i, argc, argv);
        } else if (arg == "--query") {
            opts.query = next_value(i, argc, argv).value_or("");
        } else if (arg == "--language") {
            opts.language = next_value(i, argc, argv).value_or("auto");
        } else if (arg == "--topk") {
            auto v = next_value(i, argc, argv);
            if (v) opts.topk = std::stoi(*v);
        } else if (arg == "--include-base") {
            opts.include_base = true;
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            return false;
        }
    }
    return true;
}

void print_entry(const FastVocabService::VocabEntry &e) {
    std::cout << "#" << e.id << " EN: " << (e.english.empty() ? "-" : e.english)
              << " | ZH: " << (e.chinese.empty() ? "-" : e.chinese) << "\n";
    if (!e.meaning_en.empty()) std::cout << "  meaning_en: " << e.meaning_en << "\n";
    if (!e.meaning_zh.empty()) std::cout << "  meaning_zh: " << e.meaning_zh << "\n";
}

optional<int> parse_int(const string &s) {
    try {
        return std::stoi(s);
    } catch (...) {
        return std::nullopt;
    }
}

bool manage_deleted_menu(FastVocabService &svc) {
    bool exit_once = false;
    while (true) {
        auto deleted = svc.list_deleted();
        if (deleted.empty()) {
            if (exit_once) return true;
            std::cout << "No temporarily deleted words. Type 'exit' again to quit or anything else to stay: ";
            string line;
            std::getline(std::cin, line);
            if (line == "exit" || line == "EXIT") return true;
            exit_once = true;
            continue;
        }
        std::cout << "\nTemporarily deleted words:\n";
        for (const auto &e : deleted) {
            print_entry(e);
        }
        std::cout << "Enter an ID to restore/edit, or type 'exit' to leave (need two exits to quit): ";
        string line;
        if (!std::getline(std::cin, line)) return true;
        if (line == "exit" || line == "EXIT") {
            if (exit_once) return true;
            exit_once = true;
            continue;
        }
        auto id = parse_int(line);
        if (!id) {
            std::cout << "Invalid input.\n";
            continue;
        }
        auto entry = svc.get_entry(*id);
        if (!entry || !entry->deleted) {
            std::cout << "ID not found in deleted list.\n";
            continue;
        }
        std::cout << "Choose action: (r)estore, (e)dit (keeps deleted until restored), (c)ancel: ";
        string act;
        std::getline(std::cin, act);
        if (act == "r" || act == "R") {
            if (svc.restore_entry(*id)) {
                std::cout << "Restored.\n";
            } else {
                std::cout << "Restore failed.\n";
            }
        } else if (act == "e" || act == "E") {
            std::string en, zh, men, mzh;
            std::cout << "New English (blank to keep): ";
            std::getline(std::cin, en);
            std::cout << "New Chinese (blank to keep): ";
            std::getline(std::cin, zh);
            std::cout << "New meaning_en (blank to keep): ";
            std::getline(std::cin, men);
            std::cout << "New meaning_zh (blank to keep): ";
            std::getline(std::cin, mzh);
            svc.update_entry(
                *id,
                en.empty() ? std::nullopt : optional<string>(en),
                zh.empty() ? std::nullopt : optional<string>(zh),
                men.empty() ? std::nullopt : optional<string>(men),
                mzh.empty() ? std::nullopt : optional<string>(mzh));
            std::cout << "Updated entry.\n";
        } else {
            std::cout << "Cancelled.\n";
        }
    }
}

void run_menu(FastVocabService &svc) {
    bool running = true;
    while (running) {
        std::cout << "\nChoose an option:\n"
                  << "1) Record\n"
                  << "2) Delete (temporary)\n"
                  << "3) Restore\n"
                  << "4) Find word\n"
                  << "5) Exit\n"
                  << "Selection: ";
        string choice;
        if (!std::getline(std::cin, choice)) break;
        if (choice == "1") {
            string en, zh, men, mzh;
            std::cout << "English (blank if none): ";
            std::getline(std::cin, en);
            std::cout << "Chinese (blank if none): ";
            std::getline(std::cin, zh);
            std::cout << "Meaning (EN, optional): ";
            std::getline(std::cin, men);
            std::cout << "Meaning (ZH, optional): ";
            std::getline(std::cin, mzh);
            int id = svc.record(
                en.empty() ? std::nullopt : optional<string>(en),
                zh.empty() ? std::nullopt : optional<string>(zh),
                men.empty() ? std::nullopt : optional<string>(men),
                mzh.empty() ? std::nullopt : optional<string>(mzh));
            std::cout << "Saved entry #" << id << "\n";
        } else if (choice == "2") {
            auto entries = svc.list_active();
            if (entries.empty()) {
                std::cout << "No entries to delete.\n";
                continue;
            }
            std::cout << "Entries:\n";
            for (const auto &e : entries) print_entry(e);
            std::cout << "Enter ID to temporarily delete: ";
            string line;
            std::getline(std::cin, line);
            auto id = parse_int(line);
            if (!id) {
                std::cout << "Invalid ID.\n";
                continue;
            }
            if (svc.soft_delete(*id)) {
                std::cout << "Temporarily deleted.\n";
            } else {
                std::cout << "Delete failed.\n";
            }
        } else if (choice == "3") {
            (void)manage_deleted_menu(svc);
        } else if (choice == "4") {
            std::cout << "Enter query: ";
            string q;
            std::getline(std::cin, q);
            auto hits = svc.search(q, "auto", 10, true);
            for (const auto &h : hits) {
                if (h.source == "synonym_edge" && h.extra.rfind("lang=", 0) == 0) {
                    std::cout << h.score << "\t" << h.source << "(" << h.extra.substr(5) << ")\t"
                              << h.english << " ~ " << h.chinese << "\n";
                } else {
                    std::cout << h.score << "\t" << h.source << "\tEN:" << (h.english.empty() ? "-" : h.english)
                              << "\tZH:" << (h.chinese.empty() ? "-" : h.chinese) << "\n";
                }
            }
        } else if (choice == "5") {
            running = !manage_deleted_menu(svc);
        } else {
            std::cout << "Unknown option.\n";
        }
    }
}

int main(int argc, char **argv) {
    CliOptions opts;
    const bool has_args = parse_args(argc, argv, opts);

    try {
        FastVocabService svc(has_args ? opts.db : "notebook.db");
        if (!has_args) {
            svc.initialize(std::nullopt, false);
            run_menu(svc);
            return 0;
        }
        if (opts.cmd == "init") {
            svc.initialize(opts.sql_dump, opts.rebuild);
            std::cout << "DB ready at " << opts.db << "\n";
        } else if (opts.cmd == "record") {
            svc.initialize(std::nullopt, false);
            int row_id = svc.record(opts.english, opts.chinese, opts.meaning_en, opts.meaning_zh);
            std::cout << "Saved entry #" << row_id << "\n";
        } else if (opts.cmd == "search") {
            if (opts.query.empty()) {
                std::cerr << "--query is required for search\n";
                return 1;
            }
            svc.initialize(std::nullopt, false);
            auto hits = svc.search(opts.query, opts.language, opts.topk, opts.include_base);
            for (const auto &h : hits) {
                if (h.source == "synonym_edge" && h.extra.rfind("lang=", 0) == 0) {
                    std::cout << h.score << "\t" << h.source << "(" << h.extra.substr(5) << ")\t"
                              << h.english << " ~ " << h.chinese << "\n";
                } else {
                    std::cout << h.score << "\t" << h.source << "\tEN:" << (h.english.empty() ? "-" : h.english)
                              << "\tZH:" << (h.chinese.empty() ? "-" : h.chinese) << "\n";
                }
            }
        } else {
            print_usage();
            return 1;
        }
    } catch (const std::exception &ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
    return 0;
}
