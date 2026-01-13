<<<<<<< HEAD
#ifndef ZH_AI_THESAURUS_WORD

#define ZH_AI_THESAURUS_WORD

#include <ai_thesaurus_word.h>

using namespace std;

/**
 * @brief Chinese-specialized thesaurus word.
 *
 * Adds hooks for Chinese-specific token parsing, exporting, and traversal so
 * concrete implementations can focus on file I/O while reusing the base
 * bookkeeping from aiThesaurusWord.
 */
class zhAiThesaurusWord : public aiThesaurusWord {
    protected:
        /**
         * @brief Read the next token from a CSV stream.
         * Custom parsing handles punctuation/spacing differences.
         */
        virtual bool getTokens(istringstream &iss, string &token);
        /**
         * @brief Provide a label used when exporting grouped synonyms.
         */
        virtual string getExportName() const = 0;
    public:
        /**
         * @brief Supply a stream containing Chinese synonym data.
         */
        virtual unique_ptr<ifstream> loadFile() = 0;
        /**
         * @brief Gather synonyms for a given Chinese headword.
         */
        set<string> getSynonyms(const string& word);
        /**
         * @brief Print every synonym group for quick debugging.
         */
        void printAll() const;
        /**
         * @brief Export all synonym groups to disk.
         */
        void exportAll() const;
};



#endif
=======
#ifndef ZH_AI_THESAURUS_WORD

#define ZH_AI_THESAURUS_WORD

#include <ai_thesaurus_word.h>

using namespace std;

/**
 * @brief Chinese-specialized thesaurus word.
 *
 * Adds hooks for Chinese-specific token parsing, exporting, and traversal so
 * concrete implementations can focus on file I/O while reusing the base
 * bookkeeping from aiThesaurusWord.
 */
class zhAiThesaurusWord : public aiThesaurusWord {
    protected:
        /**
         * @brief Read the next token from a CSV stream.
         * Custom parsing handles punctuation/spacing differences.
         */
        virtual bool getTokens(istringstream &iss, string &token);
        /**
         * @brief Provide a label used when exporting grouped synonyms.
         */
        virtual string getExportName() const = 0;
    public:
        /**
         * @brief Supply a stream containing Chinese synonym data.
         */
        virtual unique_ptr<ifstream> loadFile() = 0;
        /**
         * @brief Gather synonyms for a given Chinese headword.
         */
        set<string> getSynonyms(const string& word);
        /**
         * @brief Print every synonym group for quick debugging.
         */
        void printAll() const;
        /**
         * @brief Export all synonym groups to disk.
         */
        void exportAll() const;
};



#endif
>>>>>>> 792df40 (lasdfsa)
