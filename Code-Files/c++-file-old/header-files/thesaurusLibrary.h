<<<<<<< HEAD
#ifndef THESAURUS_LIBRARY
#define THESAURUS_LIBRARY

#include <map>
#include <memory>
#include <set>
#include <string>

using namespace std;
class ThesaurusLibrary {
    protected:
        map<string, set<string>> thesaurusMap;
        ThesaurusLibrary();
        void initialize();
        virtual bool getTokens(istringstream &iss, string &token);
        virtual string getExportName() const = 0;

    public:
        virtual unique_ptr<ifstream> loadFile() = 0;
        set<string> getSynonyms(const string& word);
        void printAll() const;
        void exportAll() const;
};

#endif // THESAURUS_LIBRARY
=======
#ifndef THESAURUS_LIBRARY
#define THESAURUS_LIBRARY

#include <map>
#include <memory>
#include <set>
#include <string>

using namespace std;
class ThesaurusLibrary {
    protected:
        map<string, set<string>> thesaurusMap;
        ThesaurusLibrary();
        void initialize();
        virtual bool getTokens(istringstream &iss, string &token);
        virtual string getExportName() const = 0;

    public:
        virtual unique_ptr<ifstream> loadFile() = 0;
        set<string> getSynonyms(const string& word);
        void printAll() const;
        void exportAll() const;
};

#endif // THESAURUS_LIBRARY
>>>>>>> 792df40 (lasdfsa)
