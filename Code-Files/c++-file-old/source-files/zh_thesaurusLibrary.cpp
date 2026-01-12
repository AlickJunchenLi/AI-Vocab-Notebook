#include "../header-files/zh_thesaurusLibrary.h"
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

zh_ThesaurusLibrary::zh_ThesaurusLibrary(): ThesaurusLibrary{} {}


unique_ptr<ifstream> zh_ThesaurusLibrary::loadFile() {
    return make_unique<ifstream> ("Chinese_Thesaurus\\cn_thesaurus.txt");
}

unique_ptr<zh_ThesaurusLibrary> zh_ThesaurusLibrary::create() {
    unique_ptr <zh_ThesaurusLibrary> instance = unique_ptr<zh_ThesaurusLibrary>(new zh_ThesaurusLibrary());
    instance->initialize();
    return instance;
}

bool zh_ThesaurusLibrary::getTokens(istringstream &iss, string &token) {
    return static_cast<bool>(getline(iss, token, ' '));
}

string zh_ThesaurusLibrary::getExportName() const {
    return "thesaurus_dump_cn_full.txt";
}

