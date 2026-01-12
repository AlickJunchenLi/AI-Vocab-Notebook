#ifndef WORDS_DICTIONARY

#define WORDS_DICTIONARY

#include <map>
#include <memory>
#include <string>
#include <cstring>
#include <set>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>

using namespace std;

class aiThesaurusWord;

/**
 * @brief Manager that builds and wires the thesaurus graph.
 *
 * Owns all aiThesaurusWord nodes and loads Chinese synonyms, English synonyms,
 * and bilingual translations from CSV files. Helper methods parse the CSV data
 * and connect synonym/translation edges. Public initialize* entry points expose
 * the prepared graph for downstream adapters.
 */
class wordsDictionary {
    // Master lookup of every word node.
    map <string, aiThesaurusWord *> database;
    // Chinese-only node lookup.
    map <string, aiThesaurusWord *> ZHDatabase;
    // English-only node lookup.
    map <string, aiThesaurusWord *> ENDatabase;
    wordsDictionary();
    // Populate Chinese synonym edges from the CSV data.
    void createAllChineseSynonyms();
    // Populate English synonym edges from the CSV data.
    void createAllEnglishSynonyms();
    // Populate translation edges between English and Chinese nodes.
    void createAllTranslations();
    // Load Chinese synonym file into a stream.
    unique_ptr <ifstream> loadChineseSynonymFile();
    // Load English synonym file into a stream.
    unique_ptr <ifstream> loadEnglishSynonymFile();
    // Load translation file into a stream.
    unique_ptr <ifstream> loadTranslationFile();
    // Tokenization helper for CSV parsing.
    bool getTokens(istringstream &iss, string &token);
    public:
        /**
         * @brief Initialize Chinese synonym edges after nodes are created.
         */
        void initializeChineseSynonyms();
        /**
         * @brief Initialize English synonym edges after nodes are created.
         */
        void initializeEnglishSynonyms();
        /**
         * @brief Initialize translation edges between English and Chinese nodes.
         */
        void initializeTranslations();
};



#endif
