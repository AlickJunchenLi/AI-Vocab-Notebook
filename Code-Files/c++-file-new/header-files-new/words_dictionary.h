#ifndef AI_NOTEBOOK_WORDS_DICTIONARY_H
#define AI_NOTEBOOK_WORDS_DICTIONARY_H

#include "ai_thesaurus_word.h"
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

/**
 * @brief High-level manager that builds the AI thesaurus graph.
 *
 * wordsDictionary owns every aiThesaurusWord pointer and loads three data
 * sources: Chinese synonyms, English synonyms, and bilingual translations.
 * The private helper methods read CSV files, normalize the entries, and wire
 * up the synonym/translation edges.  Public initialize* entry points expose
 * the prepared graph to adapters that want to export the data elsewhere.
 */
class wordsDictionary {
  private:
    friend class aiThesaurusWord;
    std::map<std::string, aiThesaurusWord *> database;
    std::map<std::string, aiThesaurusWord *> ZHDatabase;
    std::map<std::string, aiThesaurusWord *> ENDatabase;

    wordsDictionary();

    void createAllChineseSynonyms();
    void createAllEnglishSynonyms();
    void createAllTranslations();

    unique_ptr<std::ifstream> loadChineseSynonymFile();
    unique_ptr<std::ifstream> loadEnglishSynonymFile();
    unique_ptr<std::ifstream> loadTranslationFile();

  public:
    /**
     * @brief Populate Chinese synonym edges after the nodes exist.
     */
    void initializeChineseSynonyms();

    /**
     * @brief Populate English synonym edges after the nodes exist.
     */
    void initializeEnglishSynonyms();

    /**
     * @brief Populate translation edges between English and Chinese nodes.
     */
    void initializeTranslations();
};

#endif // AI_NOTEBOOK_WORDS_DICTIONARY_H
