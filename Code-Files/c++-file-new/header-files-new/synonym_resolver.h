<<<<<<< HEAD
#ifndef AI_NOTEBOOK_SYNONYM_RESOLVER_H
#define AI_NOTEBOOK_SYNONYM_RESOLVER_H

#include "notebook_language.h"
#include <set>
#include <string>

class VocabularyRepository;

/**
 * @brief Expands a query term into the union of synonyms and link-backed terms.
 *
 * SearchService relies on this helper to translate vague user input into a
 * useful set of candidate tokens.
 */
class SynonymResolver {
  public:
    virtual ~SynonymResolver() = default;

    virtual std::set<std::string>
    get_related_terms(const std::string &query,
                      NotebookLanguage language,
                      VocabularyRepository &repo) = 0;

    virtual std::set<std::string>
    expand_with_linked_vocab(const std::set<std::string> &terms,
                             NotebookLanguage language,
                             VocabularyRepository &repo) = 0;
};

#endif // AI_NOTEBOOK_SYNONYM_RESOLVER_H
=======
#ifndef AI_NOTEBOOK_SYNONYM_RESOLVER_H
#define AI_NOTEBOOK_SYNONYM_RESOLVER_H

#include "notebook_language.h"
#include <set>
#include <string>

class VocabularyRepository;

/**
 * @brief Expands a query term into the union of synonyms and link-backed terms.
 *
 * SearchService relies on this helper to translate vague user input into a
 * useful set of candidate tokens.
 */
class SynonymResolver {
  public:
    virtual ~SynonymResolver() = default;

    virtual std::set<std::string>
    get_related_terms(const std::string &query,
                      NotebookLanguage language,
                      VocabularyRepository &repo) = 0;

    virtual std::set<std::string>
    expand_with_linked_vocab(const std::set<std::string> &terms,
                             NotebookLanguage language,
                             VocabularyRepository &repo) = 0;
};

#endif // AI_NOTEBOOK_SYNONYM_RESOLVER_H
>>>>>>> 792df40 (lasdfsa)
