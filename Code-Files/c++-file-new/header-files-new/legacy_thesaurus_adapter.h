<<<<<<< HEAD
#ifndef AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H
#define AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H

#include "words_dictionary.h"

/**
 * @brief Bridges the legacy C++ dictionary into the SQLite-based notebook.
 *
 * The adapter owns a wordsDictionary instance, triggers every initialization
 * routine, and then exposes convenience methods that export the synonym graph
 * or translation pairs to higher level services (for example, the Python
 * importer that populates SQLite tables).  Keeping this logic isolated means
 * the rest of the application does not need to understand raw pointers or the
 * CSV storage layout used by the old project.
 */
class LegacyThesaurusAdapter {
  public:
    /**
     * @brief Build and return a fully populated dictionary for the target language.
     */
    wordsDictionary build_dictionary(LegacyLanguage language);

    /**
     * @brief Helper that loads every header/source pair and creates the dictionary.
     */
    wordsDictionary load_from_header_sources();

    /**
     * @brief Export synonym groups so downstream layers can store them elsewhere.
     */
    void export_synonym_groups(const wordsDictionary &dict);
};

#endif // AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H
=======
#ifndef AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H
#define AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H

#include "words_dictionary.h"

/**
 * @brief Bridges the legacy C++ dictionary into the SQLite-based notebook.
 *
 * The adapter owns a wordsDictionary instance, triggers every initialization
 * routine, and then exposes convenience methods that export the synonym graph
 * or translation pairs to higher level services (for example, the Python
 * importer that populates SQLite tables).  Keeping this logic isolated means
 * the rest of the application does not need to understand raw pointers or the
 * CSV storage layout used by the old project.
 */
class LegacyThesaurusAdapter {
  public:
    /**
     * @brief Build and return a fully populated dictionary for the target language.
     */
    wordsDictionary build_dictionary(LegacyLanguage language);

    /**
     * @brief Helper that loads every header/source pair and creates the dictionary.
     */
    wordsDictionary load_from_header_sources();

    /**
     * @brief Export synonym groups so downstream layers can store them elsewhere.
     */
    void export_synonym_groups(const wordsDictionary &dict);
};

#endif // AI_NOTEBOOK_LEGACY_THESAURUS_ADAPTER_H
>>>>>>> 792df40 (lasdfsa)
