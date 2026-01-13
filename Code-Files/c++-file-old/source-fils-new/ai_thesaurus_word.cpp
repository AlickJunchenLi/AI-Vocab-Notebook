<<<<<<< HEAD
#include "../header-files-new/ai_thesaurus_word.h"
#include "../header-files-new/words_dictionary.h"
#include "../header-files-new/enums.h"
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


aiThesaurusWord::aiThesaurusWord(string &queryWord, Language queryLanguage): word{queryWord}, 
    language{queryLanguage}, aiWordSynonyms{}, aiWordTranslations{} {}


=======
#include "../header-files-new/ai_thesaurus_word.h"
#include "../header-files-new/words_dictionary.h"
#include "../header-files-new/enums.h"
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


aiThesaurusWord::aiThesaurusWord(string &queryWord, Language queryLanguage): word{queryWord}, 
    language{queryLanguage}, aiWordSynonyms{}, aiWordTranslations{} {}


>>>>>>> 792df40 (lasdfsa)
