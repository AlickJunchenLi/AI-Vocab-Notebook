<<<<<<< HEAD
#ifndef AI_NOTEBOOK_FUZZY_MATCHER_H
#define AI_NOTEBOOK_FUZZY_MATCHER_H

#include <string>

/**
 * @brief Abstract interface for Levenshtein/ratio based similarity checks.
 *
 * Implementations can use python-Levenshtein, RapidFuzz, or custom code.
 * The search service only depends on these few helpers.
 */
class FuzzyMatcher {
  public:
    virtual ~FuzzyMatcher() = default;

    virtual int distance(const std::string &a, const std::string &b) const = 0;

    virtual double similarity(const std::string &a, const std::string &b) const = 0;

    virtual bool is_close(const std::string &a,
                          const std::string &b,
                          double threshold) const = 0;
};

#endif // AI_NOTEBOOK_FUZZY_MATCHER_H
=======
#ifndef AI_NOTEBOOK_FUZZY_MATCHER_H
#define AI_NOTEBOOK_FUZZY_MATCHER_H

#include <string>

/**
 * @brief Abstract interface for Levenshtein/ratio based similarity checks.
 *
 * Implementations can use python-Levenshtein, RapidFuzz, or custom code.
 * The search service only depends on these few helpers.
 */
class FuzzyMatcher {
  public:
    virtual ~FuzzyMatcher() = default;

    virtual int distance(const std::string &a, const std::string &b) const = 0;

    virtual double similarity(const std::string &a, const std::string &b) const = 0;

    virtual bool is_close(const std::string &a,
                          const std::string &b,
                          double threshold) const = 0;
};

#endif // AI_NOTEBOOK_FUZZY_MATCHER_H
>>>>>>> 792df40 (lasdfsa)
