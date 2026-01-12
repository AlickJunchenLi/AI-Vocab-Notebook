#ifndef AI_NOTEBOOK_SYNONYM_SET_H
#define AI_NOTEBOOK_SYNONYM_SET_H

#include "notebook_language.h"
#include <string>

/**
 * @brief Metadata for a synonym group imported from CSV.
 *
 * Each set groups peer terms in the same language so searches can connect
 * user queries with previously saved entries.
 */
class SynonymSet {
  public:
    int id = 0;
    NotebookLanguage language = NotebookLanguage::en;
    std::string description;
};

#endif // AI_NOTEBOOK_SYNONYM_SET_H
