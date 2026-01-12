#ifndef AI_NOTEBOOK_VOCABULARY_ENTRY_H
#define AI_NOTEBOOK_VOCABULARY_ENTRY_H

#include <string>
#include <vector>

/**
 * @brief Represents one saved vocabulary pair in the user database.
 *
 * The struct mirrors the SQLite table so higher layers can work with an
 * in-memory object instead of raw SQL rows.
 */
class VocabularyEntry {
  public:
    int id = 0;
    std::string chinese_text;
    std::string english_text;
    std::string part_of_speech;
    std::vector<std::string> tags;
    std::string notes;
    std::string created_at;
    std::string updated_at;
};

#endif // AI_NOTEBOOK_VOCABULARY_ENTRY_H
