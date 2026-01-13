<<<<<<< HEAD
#ifndef AI_NOTEBOOK_TEXT_NORMALIZER_H
#define AI_NOTEBOOK_TEXT_NORMALIZER_H

#include "notebook_language.h"
#include <string>

/**
 * @brief Provides reusable text normalization helpers.
 *
 * Search quality depends heavily on consistent token forms. The normalizer
 * performs casing, punctuation, width, and (optionally) Chinese simplification
 * before the data flows into SQLite or the synonym graph.
 */
class TextNormalizer {
  public:
    virtual ~TextNormalizer() = default;

    virtual std::string normalize(const std::string &text,
                                  NotebookLanguage language) const = 0;

    virtual std::string strip_punctuation(const std::string &text) const = 0;

    virtual std::string canonicalize_width(const std::string &text) const = 0;

    virtual std::string to_lower_ascii(const std::string &text) const = 0;

    virtual std::string simplify_chinese(const std::string &text) const = 0;
};

#endif // AI_NOTEBOOK_TEXT_NORMALIZER_H
=======
#ifndef AI_NOTEBOOK_TEXT_NORMALIZER_H
#define AI_NOTEBOOK_TEXT_NORMALIZER_H

#include "notebook_language.h"
#include <string>

/**
 * @brief Provides reusable text normalization helpers.
 *
 * Search quality depends heavily on consistent token forms. The normalizer
 * performs casing, punctuation, width, and (optionally) Chinese simplification
 * before the data flows into SQLite or the synonym graph.
 */
class TextNormalizer {
  public:
    virtual ~TextNormalizer() = default;

    virtual std::string normalize(const std::string &text,
                                  NotebookLanguage language) const = 0;

    virtual std::string strip_punctuation(const std::string &text) const = 0;

    virtual std::string canonicalize_width(const std::string &text) const = 0;

    virtual std::string to_lower_ascii(const std::string &text) const = 0;

    virtual std::string simplify_chinese(const std::string &text) const = 0;
};

#endif // AI_NOTEBOOK_TEXT_NORMALIZER_H
>>>>>>> 792df40 (lasdfsa)
