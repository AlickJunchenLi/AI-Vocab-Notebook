#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include "..\\header-files\\thesaurusLibrary.h"
#include "..\\header-files\\en_thesaurusLibrary.h"
#include "..\\header-files\\zh_thesaurusLibrary.h"
#include "..\\header-files\\noteBook.h"
#include <filesystem>
#include <map>
#include <memory>

using namespace std;

int main() {
    auto en_thesaurus = en_ThesaurusLibrary::create();
    auto zh_thesaurus = zh_ThesaurusLibrary::create();
    auto zh_to_eng = 
    auto notebook = make_unique<NoteBook>();
    en_thesaurus->exportAll();
    zh_thesaurus->exportAll();
    return 0;
}
