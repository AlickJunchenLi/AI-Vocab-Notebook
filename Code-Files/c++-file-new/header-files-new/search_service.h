<<<<<<< HEAD
#ifndef AI_NOTEBOOK_SEARCH_SERVICE_H
#define AI_NOTEBOOK_SEARCH_SERVICE_H

#include "notebook_language.h"
#include "vocabulary_entry.h"
#include <string>
#include <vector>

class VocabularyRepository;
class SynonymResolver;
class TextNormalizer;
class FuzzyMatcher;

/**
 * @brief High-level API that powers the desktop search box.
 *
 * The service glues together normalization, synonym expansion, fuzzy scoring,
 * and final ranking to return helpful vocabulary entries even when the user
 * only remembers an approximate word.
 */
class SearchService {
  public:
    virtual ~SearchService() = default;

    virtual std::vector<VocabularyEntry>
    search_vocabulary(const std::string &query_text,
                      NotebookLanguage language,
                      VocabularyRepository &repo,
                      SynonymResolver &resolver,
                      TextNormalizer &normalizer,
                      FuzzyMatcher &matcher) = 0;

  protected:
    virtual std::vector<std::string>
    collect_candidate_terms(const std::string &query_text,
                            NotebookLanguage language,
                            SynonymResolver &resolver,
                            TextNormalizer &normalizer) = 0;

    virtual std::vector<VocabularyEntry>
    rank_results(const std::vector<VocabularyEntry> &entries,
                 const std::string &query_text,
                 NotebookLanguage language,
                 FuzzyMatcher &matcher) = 0;
};

#endif // AI_NOTEBOOK_SEARCH_SERVICE_H
=======
#ifndef AI_NOTEBOOK_SEARCH_SERVICE_H
#define AI_NOTEBOOK_SEARCH_SERVICE_H

#include "notebook_language.h"
#include "vocabulary_entry.h"
#include <string>
#include <vector>

class VocabularyRepository;
class SynonymResolver;
class TextNormalizer;
class FuzzyMatcher;

/**
 * @brief High-level API that powers the desktop search box.
 *
 * The service glues together normalization, synonym expansion, fuzzy scoring,
 * and final ranking to return helpful vocabulary entries even when the user
 * only remembers an approximate word.
 */
class SearchService {
  public:
    virtual ~SearchService() = default;

    virtual std::vector<VocabularyEntry>
    search_vocabulary(const std::string &query_text,
                      NotebookLanguage language,
                      VocabularyRepository &repo,
                      SynonymResolver &resolver,
                      TextNormalizer &normalizer,
                      FuzzyMatcher &matcher) = 0;

  protected:
    virtual std::vector<std::string>
    collect_candidate_terms(const std::string &query_text,
                            NotebookLanguage language,
                            SynonymResolver &resolver,
                            TextNormalizer &normalizer) = 0;

    virtual std::vector<VocabularyEntry>
    rank_results(const std::vector<VocabularyEntry> &entries,
                 const std::string &query_text,
                 NotebookLanguage language,
                 FuzzyMatcher &matcher) = 0;
};

#endif // AI_NOTEBOOK_SEARCH_SERVICE_H
>>>>>>> 792df40 (lasdfsa)
