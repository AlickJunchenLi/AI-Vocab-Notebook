#ifndef AI_NOTEBOOK_ZH_AI_THESAURUS_WORD_H
#define AI_NOTEBOOK_ZH_AI_THESAURUS_WORD_H

#include "ai_thesaurus_word.h"
#include <fstream>
#include <memory>
#include <set>
#include <string>
#include <sstream>

using namespace std;

/**
 * @brief Chinese-specialized aiThesaurusWord.
 *
 * Chinese CSV synonym lists require custom token parsing, exporting, and
 * traversal logic.  This class defines the template methods so concrete
 * implementations can focus on file I/O without re-implementing the base
 * word bookkeeping.
 */
class zhAiThesaurusWord : public aiThesaurusWord {
  protected:

    /**
     * @brief Text description used when exporting grouped synonyms.
     */
    virtual string getExportName() const;

  public:

    /**
     * @brief Read next token from a CSV stream.
     * Custom parsing handles punctuation and whitespace that differ from
     * English CSV files.
     */
    static bool getTokens(istringstream &iss, string &token);

    zhAiThesaurusWord(const string &queryWord);
    
    /**
     * @brief Provide a ready-to-read stream populated with Chinese synonym data.
     */
    virtual unique_ptr<ifstream> loadFile();

    /**
     * @brief Collect synonyms for a given Chinese headword.
     */
    set<zhAiThesaurusWord *> getSynonyms() const;

    /**
     * @brief Print every synonym group to stdout for quick debugging.
     */
    void printAll() const;
};

#endif // AI_NOTEBOOK_ZH_AI_THESAURUS_WORD_H
