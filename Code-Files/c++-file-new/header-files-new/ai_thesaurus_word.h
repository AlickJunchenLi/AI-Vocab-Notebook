#ifndef AI_NOTEBOOK_AI_THESAURUS_WORD_H
#define AI_NOTEBOOK_AI_THESAURUS_WORD_H

#include "enums.h"
#include <memory>
#include <set>
#include <string>

using namespace std;

class wordsDictionary;

/**
 * @brief Base node that represents a single word in the AI thesaurus graph.
 *
 * Every English or Chinese word in the dictionary is an aiThesaurusWord.
 * The object stores the canonical spelling, remembers which language bucket
 * it belongs to, and owns adjacency sets with raw pointers to synonym and
 * translation peers.  wordsDictionary fills these sets as it parses CSV data,
 * so the class only exposes state needed by the graph-building logic.
 */
class aiThesaurusWord {
    friend class wordsDictionary;

  protected:
    set<aiThesaurusWord *> aiWordSynonyms;
    set<aiThesaurusWord *> aiWordTranslations;

  public:
    const string word;
    LegacyLanguage language;

    /**
     * @brief Construct a word node.
     * @param queryWord canonical spelling stored as a std::string copy
     * @param queryLanguage identifies whether the word is Chinese or English
     */
    aiThesaurusWord(const string &queryWord, LegacyLanguage queryLanguage);

    virtual ~aiThesaurusWord() = default;
};

#endif // AI_NOTEBOOK_AI_THESAURUS_WORD_H
