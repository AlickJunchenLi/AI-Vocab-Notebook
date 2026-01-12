#ifndef AI_NOTEBOOK_SYNONYM_LINKER_H
#define AI_NOTEBOOK_SYNONYM_LINKER_H

#include "notebook_language.h"
#include <string>
#include <utility>
#include <vector>

class VocabularyRepository;
class TextNormalizer;
class FuzzyMatcher;

/**
 * @brief Connects synonym terms to vocabulary entries.
 *
 * The linker runs in three passes (exact, synonym, fuzzy) and records the
 * link metadata so searches can later score matches.
 */
class SynonymLinker {
  public:
    virtual ~SynonymLinker() = default;

    virtual void link_terms_to_vocab(NotebookLanguage language,
                                     VocabularyRepository &repo,
                                     TextNormalizer &normalizer,
                                     FuzzyMatcher &matcher) = 0;

  protected:
    virtual std::vector<int>
    exact_match(const std::string &term, NotebookLanguage language) = 0;

    virtual std::vector<int>
    synonym_match(const std::string &term, NotebookLanguage language) = 0;

    virtual std::vector<std::pair<int, double>>
    fuzzy_match(const std::string &term,
                NotebookLanguage language,
                FuzzyMatcher &matcher) = 0;
};

#endif // AI_NOTEBOOK_SYNONYM_LINKER_H
