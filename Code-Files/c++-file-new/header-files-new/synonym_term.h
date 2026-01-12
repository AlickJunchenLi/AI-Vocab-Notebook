#ifndef AI_NOTEBOOK_SYNONYM_TERM_H
#define AI_NOTEBOOK_SYNONYM_TERM_H

#include <string>

/**
 * @brief Single word/phrase inside a synonym set.
 *
 * Stores both the raw token from the CSV and a normalized version to make
 * joins faster when running search queries.
 */
class SynonymTerm {
  public:
    int id = 0;
    int set_id = 0;
    std::string term_text;
    std::string normalized_text;
};

#endif // AI_NOTEBOOK_SYNONYM_TERM_H
