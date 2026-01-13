<<<<<<< HEAD
#ifndef AI_THESAURUS_WORD

#define AI_THESAUTUS_WORD

#include "enums.h"
#include <map>
#include <string>
#include <cstring>
#include <set>
#include <memory>

using namespace std;

class wordsDictionary;

/**
 * @brief Base node representing a single word in the thesaurus graph.
 *
 * Each entry stores the canonical spelling, knows which language bucket it
 * belongs to, and keeps adjacency sets for synonyms and translations. The
 * wordsDictionary friend class fills these sets when it parses CSV data.
 */
class aiThesaurusWord {
    friend class wordsDictionary;
    protected:
        // Synonym neighbors for this word.
        set <aiThesaurusWord *> aiWordSynonyms;
        // Translation counterparts for this word.
        set <aiThesaurusWord *> aiWordTranslations;
    public:
        // Canonical spelling of the word.
        const string word;
        // Language tag (Chinese or English) for this word.
        enum Language language;
        /**
         * @brief Construct a word node with its spelling and language.
         */
        aiThesaurusWord(string &queryWord, Language queryLanguage);
};

#endif
=======
#ifndef AI_THESAURUS_WORD

#define AI_THESAUTUS_WORD

#include "enums.h"
#include <map>
#include <string>
#include <cstring>
#include <set>
#include <memory>

using namespace std;

class wordsDictionary;

/**
 * @brief Base node representing a single word in the thesaurus graph.
 *
 * Each entry stores the canonical spelling, knows which language bucket it
 * belongs to, and keeps adjacency sets for synonyms and translations. The
 * wordsDictionary friend class fills these sets when it parses CSV data.
 */
class aiThesaurusWord {
    friend class wordsDictionary;
    protected:
        // Synonym neighbors for this word.
        set <aiThesaurusWord *> aiWordSynonyms;
        // Translation counterparts for this word.
        set <aiThesaurusWord *> aiWordTranslations;
    public:
        // Canonical spelling of the word.
        const string word;
        // Language tag (Chinese or English) for this word.
        enum Language language;
        /**
         * @brief Construct a word node with its spelling and language.
         */
        aiThesaurusWord(string &queryWord, Language queryLanguage);
};

#endif
>>>>>>> 792df40 (lasdfsa)
