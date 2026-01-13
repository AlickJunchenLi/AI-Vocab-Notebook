<<<<<<< HEAD
#include "..\\header-files-new\\en_ai_thesaurus_word.h"
#include "..\\header-files-new\\ai_thesaurus_word.h"
#include "..\\header-files-new\\get_tokens_helper_functions.h"

#include <iostream>
#include <sstream>
#include <fstream>
#include <string>


using namespace std;


enAiThesaurusWord::enAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::english} {}


bool enAiThesaurusWord::getTokens(istringstream &iss, string &token) {
    auto trimEnglish = [](string &text) {
        auto ltrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                else if (isspace(static_cast<unsigned char>(s.front()))) { s.erase(s.begin()); continue; }
                break;
            }
        };
        auto rtrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                else if (isspace(static_cast<unsigned char>(s.back()))) { s.erase(s.end()); continue; }
                break;
            }
        };
        ltrim(text);
        rtrim(text);
    };

    while (advancedGetline(iss, token, ", \t")) {
        trimEnglish(token);
        if (!token.empty()) {
            return true;
        }
    }
    return false;
}
=======
#include "..\\header-files-new\\en_ai_thesaurus_word.h"
#include "..\\header-files-new\\ai_thesaurus_word.h"
#include "..\\header-files-new\\get_tokens_helper_functions.h"

#include <iostream>
#include <sstream>
#include <fstream>
#include <string>


using namespace std;


enAiThesaurusWord::enAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::english} {}


bool enAiThesaurusWord::getTokens(istringstream &iss, string &token) {
    auto trimEnglish = [](string &text) {
        auto ltrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                else if (isspace(static_cast<unsigned char>(s.front()))) { s.erase(s.begin()); continue; }
                break;
            }
        };
        auto rtrim = [](string &s) {
            for (;;) {
                if (s.empty()) break;
                else if (isspace(static_cast<unsigned char>(s.back()))) { s.erase(s.end()); continue; }
                break;
            }
        };
        ltrim(text);
        rtrim(text);
    };

    while (advancedGetline(iss, token, ", \t")) {
        trimEnglish(token);
        if (!token.empty()) {
            return true;
        }
    }
    return false;
}
>>>>>>> 792df40 (lasdfsa)
