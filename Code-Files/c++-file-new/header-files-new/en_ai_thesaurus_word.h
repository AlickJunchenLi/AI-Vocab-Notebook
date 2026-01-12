#ifndef AI_NOTEBOOK_EN_AI_THESAURUS_WORD_H
#define AI_NOTEBOOK_EN_AI_THESAURUS_WORD_H

#include "ai_thesaurus_word.h"

using namespace std;
/**
 * @brief English-specific subclass of aiThesaurusWord.
 *
 * The class exists so english-only helpers or parsing routines can be attached
 * without polluting the shared base type.  For now it simply inherits every
 * base capability and allows future enhancements (for example, stemming or
 * British vs. American spelling normalization) to live behind a dedicated type.
 */
class enAiThesaurusWord : public aiThesaurusWord {
  protected:
  public:
    static bool getTokens(istringstream &iss, string &token);
    explicit enAiThesaurusWord(const string &queryWord);
};

#endif // AI_NOTEBOOK_EN_AI_THESAURUS_WORD_H
