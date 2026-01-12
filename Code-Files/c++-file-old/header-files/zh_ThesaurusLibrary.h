#ifndef ZH_THESAURUS_LIBRARY
#define ZH_THESAURUS_LIBRARY

#include <thesaurusLibrary.h>
#include <map>
#include <memory>
#include <set>
#include <string>

using namespace std;
class zh_ThesaurusLibrary : public ThesaurusLibrary {
    protected:
        zh_ThesaurusLibrary();
        bool getTokens(istringstream &iss, string &token)  override;
        string getExportName() const override;
    public:
        static unique_ptr<zh_ThesaurusLibrary> create();
        unique_ptr<ifstream> loadFile() override;
};

#endif