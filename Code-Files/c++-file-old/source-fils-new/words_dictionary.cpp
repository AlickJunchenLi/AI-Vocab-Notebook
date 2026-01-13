<<<<<<< HEAD
#include "../header-files-new/words_dictionary.h"
#include "../header-files-new/ai_thesaurus_word.h"
#include "../header-files-new/enums.h"
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

wordsDictionary::wordsDictionary() {
    createAllChineseSynonyms();
    createAllEnglishSynonyms();
    createAllTranslations();
    initializeChineseSynonyms();
    initializeEnglishSynonyms();
}

unique_ptr <ifstream> wordsDictionary::loadChineseSynonymFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\Chinese_Thesaurus\\cn_thesaurus.txt");
}

unique_ptr <ifstream> wordsDictionary::loadEnglishSynonymFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\English_Thesaurus\\WordnetThesaurus.csv");
}

unique_ptr <ifstream> wordsDictionary::loadTranslationFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\Translation_Dictionary\\ecdict.csv");
}

bool wordsDictionary::getTokens(istringstream &iss, string &token) {
    return static_cast <bool> (getline(iss, token, ','));
}

void wordsDictionary::createAllChineseSynonyms() {
    unique_ptr <ifstream> fin_ptr = loadChineseSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Chinese_Thesaurus\\cn_thesaurus.txt" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        istringstream iss(line);
        vector <string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (database.find(token) == database.end()) {
                aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::chinese);
                database.emplace(token, tmp_word_store);
                ZHDatabase.emplace(token, tmp_word_store);
            }
        }
    }
    fin.close();
    return;
}

void wordsDictionary::createAllEnglishSynonyms() {
    unique_ptr <ifstream> fin_ptr = loadEnglishSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open English_Thesaurus\\WordnetThesaurus.csv" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        istringstream iss(line);
        vector <string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (database.find(token) == database.end()) {
                aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::english);
                database.emplace(token, tmp_word_store);
                ENDatabase.emplace(token, tmp_word_store);
            }
        }
    }
    fin.close();
    return;
}

void wordsDictionary::createAllTranslations() {
    unique_ptr <ifstream> fin_ptr = loadTranslationFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Translation_Dictionary\\ecdict.csv" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };
    string line;
    bool isTheFirstLoop = true;
    while (getline(fin, line)) {
        if (isTheFirstLoop) {
            isTheFirstLoop = false;
            continue;
        }
        if (line.empty()) {
            continue;
        }
        istringstream iss{line};
        vector <string> tokens;
        string token;
        int loop_index = 0;
        while (getTokens(iss, token)) {
            trim(token);
            if (loop_index == 4) break;
            else if (loop_index == 0) {
                if (database.find(tokens[loop_index]) == database.end()) {
                    aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::english);
                    database.emplace(token, tmp_word_store);
                    ZHDatabase.emplace(token, tmp_word_store);
                }
            } else if (loop_index == 3) {
                if (database.find(tokens[loop_index]) == database.end()) {
                    aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::chinese);
                    database.emplace(token, tmp_word_store);
                    ENDatabase.emplace(token, tmp_word_store);
                }
            }
            loop_index++;
        }
    }
    fin.close();
    return;
}

void wordsDictionary::initializeChineseSynonyms() {
    unique_ptr<ifstream> fin_ptr = loadChineseSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Chinese_Thesaurus\\cn_thesaurus.txt" << endl;
        return;
    }

    const auto trim = [](string& text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    int i = 0;
    while (getline(fin, line)) {
        i++;
        if (line.empty()) {
            continue;
        }

        istringstream iss(line);
        vector<string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (!token.empty()) {
                tokens.emplace_back(move(token));
            }
        }

        if (tokens.empty()) {
            continue;
        }
        for (size_t idxHeadword = 0; idxHeadword < tokens.size(); ++idxHeadword) {
            const string& headword = tokens[idxHeadword];
            for (size_t idxSynonym = 0; idxSynonym < tokens.size(); ++idxSynonym) {
                if (idxSynonym == idxHeadword) {
                    continue;
                }
                database[headword]->aiWordSynonyms.emplace(tokens[idxSynonym]);
            }
        }
        
    }
    cout << i << endl;
    fin.close();
}

void wordsDictionary::initializeEnglishSynonyms() {
    unique_ptr<ifstream> fin_ptr = loadEnglishSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open English_Thesaurus\\WordnetThesaurus.csv" << endl;
        return;
    }

    const auto trim = [](string& text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    int i = 0;
    while (getline(fin, line)) {
        i++;
        if (line.empty()) {
            continue;
        }

        istringstream iss(line);
        vector<string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (!token.empty()) {
                tokens.emplace_back(move(token));
            }
        }

        if (tokens.empty()) {
            continue;
        }
        for (size_t idxHeadword = 0; idxHeadword < tokens.size(); ++idxHeadword) {
            const string& headword = tokens[idxHeadword];
            for (size_t idxSynonym = 0; idxSynonym < tokens.size(); ++idxSynonym) {
                if (idxSynonym == idxHeadword) {
                    continue;
                }
                database[headword]->aiWordSynonyms.emplace(tokens[idxSynonym]);
            }
        }
    }
    cout << i << endl;
    fin.close();
}

void wordsDictionary::initializeTranslations() {
    unique_ptr <ifstream> fin_ptr = loadTranslationFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Translation_Dictionary\\ecdict.csv" << endl;
        return;
    }
    string line;
    int i = 0;
    while (getline(fin, line)) {
        if (i == 4) break;
        else if (i == 0) {
            
        }
    }
}

=======
#include "../header-files-new/words_dictionary.h"
#include "../header-files-new/ai_thesaurus_word.h"
#include "../header-files-new/enums.h"
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

wordsDictionary::wordsDictionary() {
    createAllChineseSynonyms();
    createAllEnglishSynonyms();
    createAllTranslations();
    initializeChineseSynonyms();
    initializeEnglishSynonyms();
}

unique_ptr <ifstream> wordsDictionary::loadChineseSynonymFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\Chinese_Thesaurus\\cn_thesaurus.txt");
}

unique_ptr <ifstream> wordsDictionary::loadEnglishSynonymFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\English_Thesaurus\\WordnetThesaurus.csv");
}

unique_ptr <ifstream> wordsDictionary::loadTranslationFile() {
    return make_unique <ifstream> ("Unchanged-Databases\\Translation_Dictionary\\ecdict.csv");
}

bool wordsDictionary::getTokens(istringstream &iss, string &token) {
    return static_cast <bool> (getline(iss, token, ','));
}

void wordsDictionary::createAllChineseSynonyms() {
    unique_ptr <ifstream> fin_ptr = loadChineseSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Chinese_Thesaurus\\cn_thesaurus.txt" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        istringstream iss(line);
        vector <string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (database.find(token) == database.end()) {
                aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::chinese);
                database.emplace(token, tmp_word_store);
                ZHDatabase.emplace(token, tmp_word_store);
            }
        }
    }
    fin.close();
    return;
}

void wordsDictionary::createAllEnglishSynonyms() {
    unique_ptr <ifstream> fin_ptr = loadEnglishSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open English_Thesaurus\\WordnetThesaurus.csv" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    while (getline(fin, line)) {
        if (line.empty()) {
            continue;
        }
        istringstream iss(line);
        vector <string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (database.find(token) == database.end()) {
                aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::english);
                database.emplace(token, tmp_word_store);
                ENDatabase.emplace(token, tmp_word_store);
            }
        }
    }
    fin.close();
    return;
}

void wordsDictionary::createAllTranslations() {
    unique_ptr <ifstream> fin_ptr = loadTranslationFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Translation_Dictionary\\ecdict.csv" << endl;
    }

    const auto trim = [](string &text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };
    string line;
    bool isTheFirstLoop = true;
    while (getline(fin, line)) {
        if (isTheFirstLoop) {
            isTheFirstLoop = false;
            continue;
        }
        if (line.empty()) {
            continue;
        }
        istringstream iss{line};
        vector <string> tokens;
        string token;
        int loop_index = 0;
        while (getTokens(iss, token)) {
            trim(token);
            if (loop_index == 4) break;
            else if (loop_index == 0) {
                if (database.find(tokens[loop_index]) == database.end()) {
                    aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::english);
                    database.emplace(token, tmp_word_store);
                    ZHDatabase.emplace(token, tmp_word_store);
                }
            } else if (loop_index == 3) {
                if (database.find(tokens[loop_index]) == database.end()) {
                    aiThesaurusWord *tmp_word_store = new aiThesaurusWord(token, Language::chinese);
                    database.emplace(token, tmp_word_store);
                    ENDatabase.emplace(token, tmp_word_store);
                }
            }
            loop_index++;
        }
    }
    fin.close();
    return;
}

void wordsDictionary::initializeChineseSynonyms() {
    unique_ptr<ifstream> fin_ptr = loadChineseSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Chinese_Thesaurus\\cn_thesaurus.txt" << endl;
        return;
    }

    const auto trim = [](string& text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    int i = 0;
    while (getline(fin, line)) {
        i++;
        if (line.empty()) {
            continue;
        }

        istringstream iss(line);
        vector<string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (!token.empty()) {
                tokens.emplace_back(move(token));
            }
        }

        if (tokens.empty()) {
            continue;
        }
        for (size_t idxHeadword = 0; idxHeadword < tokens.size(); ++idxHeadword) {
            const string& headword = tokens[idxHeadword];
            for (size_t idxSynonym = 0; idxSynonym < tokens.size(); ++idxSynonym) {
                if (idxSynonym == idxHeadword) {
                    continue;
                }
                database[headword]->aiWordSynonyms.emplace(tokens[idxSynonym]);
            }
        }
        
    }
    cout << i << endl;
    fin.close();
}

void wordsDictionary::initializeEnglishSynonyms() {
    unique_ptr<ifstream> fin_ptr = loadEnglishSynonymFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open English_Thesaurus\\WordnetThesaurus.csv" << endl;
        return;
    }

    const auto trim = [](string& text) {
        const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
        text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
        text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    };

    string line;
    int i = 0;
    while (getline(fin, line)) {
        i++;
        if (line.empty()) {
            continue;
        }

        istringstream iss(line);
        vector<string> tokens;
        string token;
        while (getTokens(iss, token)) {
            trim(token);
            if (!token.empty()) {
                tokens.emplace_back(move(token));
            }
        }

        if (tokens.empty()) {
            continue;
        }
        for (size_t idxHeadword = 0; idxHeadword < tokens.size(); ++idxHeadword) {
            const string& headword = tokens[idxHeadword];
            for (size_t idxSynonym = 0; idxSynonym < tokens.size(); ++idxSynonym) {
                if (idxSynonym == idxHeadword) {
                    continue;
                }
                database[headword]->aiWordSynonyms.emplace(tokens[idxSynonym]);
            }
        }
    }
    cout << i << endl;
    fin.close();
}

void wordsDictionary::initializeTranslations() {
    unique_ptr <ifstream> fin_ptr = loadTranslationFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open Translation_Dictionary\\ecdict.csv" << endl;
        return;
    }
    string line;
    int i = 0;
    while (getline(fin, line)) {
        if (i == 4) break;
        else if (i == 0) {
            
        }
    }
}

>>>>>>> 792df40 (lasdfsa)
