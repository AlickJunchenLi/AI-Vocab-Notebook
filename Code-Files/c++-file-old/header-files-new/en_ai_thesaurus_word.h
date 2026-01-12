#ifndef EN_AI_THESAURUS_WORD

#define EN_AI_THESAURUS_WORD

#include <ai_thesaurus_word.h>

using namespace std;

/**
 * @brief English-specific specialization of aiThesaurusWord.
 *
 * Exists to hang English-only helpers without changing the shared base type.
 */
class enAiThesaurusWord : public aiThesaurusWord {
    protected:
        
    public:
};



#endif
