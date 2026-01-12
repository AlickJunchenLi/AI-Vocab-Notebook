#include "../header-files/thesaurusLibrary.h"
#include <filesystem>
#include <map>
#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>
#include <memory>

using namespace std;



ThesaurusLibrary::ThesaurusLibrary() = default;


bool ThesaurusLibrary::getTokens(istringstream &iss, string &token) {
    return static_cast<bool>(getline(iss, token, ','));
}


void ThesaurusLibrary::initialize() {
    unique_ptr<ifstream> fin_ptr = loadFile();
    ifstream &fin = *fin_ptr;
    if (!fin.is_open()) {
        cerr << "Failed to open English_Thesaurus\\WordnetThesaurus.csv" << endl;
        return;
    }

    thesaurusMap.clear();

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
            auto& synonyms = thesaurusMap[tokens[idxHeadword]];
            synonyms.emplace(headword);
            for (size_t idxSynonym = 0; idxSynonym < tokens.size(); ++idxSynonym) {
                if (idxSynonym == idxHeadword) {
                    continue;
                }
                synonyms.emplace(tokens[idxSynonym]);
            }
        }
        
    }
    cout << i << endl;
    fin.close();
}




set<string> ThesaurusLibrary::getSynonyms(const string& word) {
    if (thesaurusMap.find(word) != thesaurusMap.end()) {
        return thesaurusMap[word];
    } else {
        return {};
    }
}


void ThesaurusLibrary::printAll() const {\
    int i = 0;
    for (const auto& [word, synonyms] : thesaurusMap) {
        i++;
        //if (i == 100) return;
        cout << word << ": ";
        bool first = true;
        for (const auto& synonym : synonyms) {
            if (!first) {
                cout << ", ";
            }
            cout << synonym;
            first = false;
        }
        cout << endl;
    }
}

void ThesaurusLibrary::exportAll() const {
    int i = 0;
    ofstream fout(getExportName());
    for (const auto& [word, synonyms] : thesaurusMap) {
        i++;
        //if (i == 100) return;
        fout << word << ": ";
        bool first = true;
        for (const auto& synonym : synonyms) {
            if (!first) {
                fout << ", ";
            }
            fout << synonym;
            first = false;
        }
        fout << endl;
    }
    return;
}
