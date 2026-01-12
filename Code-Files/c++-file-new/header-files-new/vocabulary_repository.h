#ifndef AI_NOTEBOOK_VOCABULARY_REPOSITORY_H
#define AI_NOTEBOOK_VOCABULARY_REPOSITORY_H

#include "notebook_language.h"
#include "synonym_term.h"
#include "vocabulary_entry.h"
#include <memory>
#include <set>
#include <string>
#include <vector>

/**
 * @brief Thin data-access layer for the SQLite vocabulary database.
 *
 * The repository wraps connection management and exposes a handful of
 * focused operations so importers and the search service can share logic.
 */
class VocabularyRepository {
  public:
    virtual ~VocabularyRepository() = default;

    /**
     * @brief Open a connection to the on-disk SQLite database.
     */
    virtual void connect(const std::string &db_path) = 0;

    /**
     * @brief Persist a single VocabularyEntry (insert or update).
     */
    virtual void insert_entry(const VocabularyEntry &entry) = 0;

    /**
     * @brief Bulk insert helper for importer performance.
     */
    virtual void bulk_insert(const std::vector<VocabularyEntry> &entries) = 0;

    /**
     * @brief Record a link between a vocabulary entry and a synonym term.
     */
    virtual void attach_synonym(int vocab_id,
                                int term_id,
                                const std::string &kind,
                                double score) = 0;

    /**
     * @brief Return vocabulary entries matching any of the normalized terms.
     */
    virtual std::vector<VocabularyEntry>
    search_by_terms(const std::set<std::string> &terms,
                    NotebookLanguage language) = 0;

    /**
     * @brief Fetch every synonym term that equals the normalized token.
     */
    virtual std::set<SynonymTerm>
    fetch_synonyms(const std::string &normalized,
                   NotebookLanguage language) = 0;
};

#endif // AI_NOTEBOOK_VOCABULARY_REPOSITORY_H
