<<<<<<< HEAD
#include "..\header-files-new\get_tokens_helper_functions.h"

#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include <algorithm>

using namespace std;

// Already has one in words_dictionary, save this for a raindy day:)
void dictionaryTrim(string &text) {
    const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
    text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
    text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    return;
}


bool advancedGetline (istream &in, string &out, const string &delims) {
    out.clear();
    char ch;
    while (in.get(ch)) {
        if (delims.find(ch) != string::npos) {
            return true;
        } else if (ch == '\n') {
            return true;
        }
        out.push_back(ch);
    }
    return !out.empty();
}

=======
#include "..\header-files-new\get_tokens_helper_functions.h"

#include <iostream>
#include <sstream>
#include <fstream>
#include <string>
#include <algorithm>

using namespace std;

// Already has one in words_dictionary, save this for a raindy day:)
void dictionaryTrim(string &text) {
    const auto notSpace = [](unsigned char ch) { return !isspace(ch); };
    text.erase(text.begin(), find_if(text.begin(), text.end(), notSpace));
    text.erase(find_if(text.rbegin(), text.rend(), notSpace).base(), text.end());
    return;
}


bool advancedGetline (istream &in, string &out, const string &delims) {
    out.clear();
    char ch;
    while (in.get(ch)) {
        if (delims.find(ch) != string::npos) {
            return true;
        } else if (ch == '\n') {
            return true;
        }
        out.push_back(ch);
    }
    return !out.empty();
}

>>>>>>> 792df40 (lasdfsa)
