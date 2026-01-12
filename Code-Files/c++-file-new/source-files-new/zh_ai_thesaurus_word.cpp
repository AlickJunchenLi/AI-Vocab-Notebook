#include "..\\header-files-new\\zh_ai_thesaurus_word.h"
#include "..\\header-files-new\\ai_thesaurus_word.h"
#include "..\\header-files-new\\words_dictionary.h"
#include "..\\header-files-new\\get_tokens_helper_functions.h"
#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include <memory>
#include <algorithm>
#include <cctype>

using namespace std;


zhAiThesaurusWord::zhAiThesaurusWord(const string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::chinese} {}


bool zhAiThesaurusWord::getTokens(istringstream &iss, string &token) {
    // Chinese rows mix ASCII commas, full-width commas, and spaces.
    // Skip empty segments so double delimiters don't produce blanks.
    auto trimChinese = [](string &text) {
        // Trim ASCII whitespace and UTF-8 full-width space (\u3000).
        auto ltrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                if (isspace(static_cast<unsigned char>(s.front()))) { s.erase(s.begin()); continue; }
                if (s.size() >= 3 && s.compare(0, 3, "\xE3\x80\x80") == 0) { s.erase(0, 3); continue; }
                break;
            }
        };
        auto rtrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                if (isspace(static_cast<unsigned char>(s.back()))) { s.pop_back(); continue; }
                if (s.size() >= 3 && s.compare(s.size() - 3, 3, "\xE3\x80\x80") == 0) { s.erase(s.size() - 3); continue; }
                break;
            }
        };
        ltrim(text);
        rtrim(text);
    };

    while (advancedGetline(iss, token, ",\uFF0C \t")) {
        trimChinese(token);
        if (!token.empty()) {
            return true;
        }
    }
    return false;
}


string zhAiThesaurusWord::getExportName() const {
    return "Chinese Thesaurus";
}


unique_ptr<ifstream> zhAiThesaurusWord::loadFile() {
    return make_unique<ifstream>("Unchanged-Databases\\Chinese_Thesaurus\\cn_thesaurus.txt");
}


set<zhAiThesaurusWord *> zhAiThesaurusWord::getSynonyms() const {
    set<zhAiThesaurusWord *> result;
    for (aiThesaurusWord *base : aiWordSynonyms) {
        if (!base) {
            continue;
        }
        if (base->language != LegacyLanguage::chinese) {
            continue;
        }
        if (auto *zh = dynamic_cast<zhAiThesaurusWord *>(base)) {
            result.insert(zh);
        }
    }
    return result;
}

void zhAiThesaurusWord::printAll() const {
    cout << "The word is/本文字" << endl << word << endl;

    cout << "Synonyms/同义词" << endl;
    for (auto &synonyms : aiWordSynonyms) {
        cout << synonyms->word << endl;
    }

    cout << endl << "Translations/翻译" << endl;
    for (auto &translations : aiWordTranslations) {
        cout << translations->word << endl;
    }

    return;
}