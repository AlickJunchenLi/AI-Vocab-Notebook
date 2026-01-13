<<<<<<< HEAD
#include "../header-files/en_thesaurusLibrary.h"
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

en_ThesaurusLibrary::en_ThesaurusLibrary(): ThesaurusLibrary{} {}


unique_ptr<ifstream> en_ThesaurusLibrary::loadFile() {
    return make_unique<ifstream> ("English_Thesaurus\\WordnetThesaurus.csv");
}

unique_ptr<en_ThesaurusLibrary> en_ThesaurusLibrary::create() {
    unique_ptr <en_ThesaurusLibrary> instance = unique_ptr<en_ThesaurusLibrary>(new en_ThesaurusLibrary());
    instance->initialize();
    return instance;
}

bool en_ThesaurusLibrary::getTokens(istringstream &iss, string &token) {
    return static_cast<bool>(getline(iss, token, ','));
}

string en_ThesaurusLibrary::getExportName() const {
    return "thesaurus_dump_en_full.txt";
}
=======
#include "../header-files/en_thesaurusLibrary.h"
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

en_ThesaurusLibrary::en_ThesaurusLibrary(): ThesaurusLibrary{} {}


unique_ptr<ifstream> en_ThesaurusLibrary::loadFile() {
    return make_unique<ifstream> ("English_Thesaurus\\WordnetThesaurus.csv");
}

unique_ptr<en_ThesaurusLibrary> en_ThesaurusLibrary::create() {
    unique_ptr <en_ThesaurusLibrary> instance = unique_ptr<en_ThesaurusLibrary>(new en_ThesaurusLibrary());
    instance->initialize();
    return instance;
}

bool en_ThesaurusLibrary::getTokens(istringstream &iss, string &token) {
    return static_cast<bool>(getline(iss, token, ','));
}

string en_ThesaurusLibrary::getExportName() const {
    return "thesaurus_dump_en_full.txt";
}
>>>>>>> 792df40 (lasdfsa)
