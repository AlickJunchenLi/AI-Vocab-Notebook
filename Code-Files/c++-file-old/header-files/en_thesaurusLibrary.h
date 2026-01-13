<<<<<<< HEAD
#ifndef EN_THESAURUS_LIBRARY
#define EN_THESAURUS_LIBRARY

#include <thesaurusLibrary.h>
#include <map>
#include <memory>
#include <set>
#include <string>

using namespace std;
class en_ThesaurusLibrary : public ThesaurusLibrary {
    protected:
        en_ThesaurusLibrary();
        bool getTokens(istringstream &iss, string &token)  override;
        string getExportName() const override;
    public:
        static unique_ptr<en_ThesaurusLibrary> create();
        unique_ptr<ifstream> loadFile() override;
};

=======
#ifndef EN_THESAURUS_LIBRARY
#define EN_THESAURUS_LIBRARY

#include <thesaurusLibrary.h>
#include <map>
#include <memory>
#include <set>
#include <string>

using namespace std;
class en_ThesaurusLibrary : public ThesaurusLibrary {
    protected:
        en_ThesaurusLibrary();
        bool getTokens(istringstream &iss, string &token)  override;
        string getExportName() const override;
    public:
        static unique_ptr<en_ThesaurusLibrary> create();
        unique_ptr<ifstream> loadFile() override;
};

>>>>>>> 792df40 (lasdfsa)
#endif