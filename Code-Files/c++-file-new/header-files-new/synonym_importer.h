#ifndef AI_NOTEBOOK_SYNONYM_IMPORTER_H
#define AI_NOTEBOOK_SYNONYM_IMPORTER_H

#include "notebook_language.h"
#include <string>

class VocabularyRepository;

/**
 * @brief Imports synonym CSV files for either language.
 *
 * Groups rows by synonym set, normalizes terms, and sends the result to the
 * repository.  Keeping the logic here simplifies testing and reuse.
 */
class SynonymImporter {
  public:
    NotebookLanguage language;

    explicit SynonymImporter(NotebookLanguage lang) : language(lang) {}
    virtual ~SynonymImporter() = default;

    virtual void import_synonym_csv(const std::string &path,
                                    VocabularyRepository &repo,
                                    int batch_id) = 0;
};

#endif // AI_NOTEBOOK_SYNONYM_IMPORTER_H
