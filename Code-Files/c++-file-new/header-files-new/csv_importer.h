#ifndef AI_NOTEBOOK_CSV_IMPORTER_H
#define AI_NOTEBOOK_CSV_IMPORTER_H

#include <string>

class VocabularyRepository;

/**
 * @brief Handles CSV ingestion for translations and user vocab.
 *
 * The importer normalizes each row and delegates persistence to the
 * VocabularyRepository so the rest of the application stays decoupled from
 * CSV file formats.
 */
class CsvImporter {
  public:
    virtual ~CsvImporter() = default;

    virtual void import_translation_csv(const std::string &path,
                                        VocabularyRepository &repo,
                                        int batch_id) = 0;

    virtual void import_user_vocab(const std::string &path,
                                   VocabularyRepository &repo) = 0;
};

#endif // AI_NOTEBOOK_CSV_IMPORTER_H
