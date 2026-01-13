<<<<<<< HEAD
AI_VOCAB_NOTEBOOK – Project Design Overview
===========================================

This document explains the overall plan for the project, with a focus on:

- What each major class represents.
- The meaning of every field and method in the C++ headers under `c++-file-new/header-files-new`.
- How data flows from the legacy thesaurus files into the modern notebook/search stack.
- Where `zhAiThesaurusWord` fits into the design.

The goal is to give you a clear mental model so you can extend or refactor the code confidently.


1. High-Level Architecture
--------------------------

The project has two “layers”:

1. **Legacy thesaurus layer (C++ in this repo)**  
   - Works with raw text files:
     - `Unchanged-Databases/Chinese_Thesaurus/cn_thesaurus.txt`
     - `Unchanged-Databases/English_Thesaurus/WordnetThesaurus.csv`
     - `Unchanged-Databases/Translation_Dictionary/ecdict.csv`
   - Builds an in-memory graph of words and edges (synonyms and translations).
   - `wordsDictionary` and `aiThesaurusWord` are the core of this layer.

2. **Modern notebook/search layer (SQLite + abstractions)**  
   - Uses a normalized vocabulary database (SQLite) with tables like vocabulary entries, synonym sets, synonym terms, and links.
   - Adds search and fuzzy matching on top.
   - Classes like `VocabularyEntry`, `VocabularyRepository`, `SearchService`, `SynonymResolver`, `TextNormalizer`, `FuzzyMatcher`, `CsvImporter` live here.

`LegacyThesaurusAdapter` is the bridge between these two worlds: it builds the legacy graph, then exports the data into a form the notebook/search layer can consume.


2. Core Enums and Basic Data Types
----------------------------------

### 2.1 `LegacyLanguage` (`enums.h`)

```cpp
enum LegacyLanguage {
    chinese,
    english
};
```

- **Purpose**: Identifies which language a legacy thesaurus word belongs to.
- **Values**:
  - `chinese` – Simplified Chinese entries from `cn_thesaurus.txt` or translation CSV.
  - `english` – English entries from WordNet or translation CSV.

Used by: `aiThesaurusWord`, `wordsDictionary`, `LegacyThesaurusAdapter`.


### 2.2 `NotebookLanguage` (`notebook_language.h`)

```cpp
enum class NotebookLanguage {
    zh,
    en
};
```

- **Purpose**: Language flag used by the modern notebook/search stack.
- **Values**:
  - `NotebookLanguage::zh` – Chinese.
  - `NotebookLanguage::en` – English.

Used by: `SearchService`, `VocabularyRepository`, `SynonymSet`, `SynonymResolver`, `TextNormalizer`.


### 2.3 `VocabularyEntry` (`vocabulary_entry.h`)

```cpp
class VocabularyEntry {
  public:
    int id = 0;
    std::string chinese_text;
    std::string english_text;
    std::string part_of_speech;
    std::vector<std::string> tags;
    std::string notes;
    std::string created_at;
    std::string updated_at;
};
```

- **Purpose**: In-memory representation of a single row in the user’s vocabulary table.
- **Fields**:
  - `id` – Primary key from SQLite.
  - `chinese_text` – The Chinese side of the vocabulary pair.
  - `english_text` – The English side.
  - `part_of_speech` – POS tag, e.g. `"noun"`, `"verb"`.
  - `tags` – Arbitrary labels to group entries (e.g., `"HSK3"`, `"work"`).
  - `notes` – Free-form user notes.
  - `created_at` / `updated_at` – Timestamps as strings (e.g., ISO 8601).


### 2.4 `SynonymSet` (`synonym_set.h`)

```cpp
class SynonymSet {
  public:
    int id = 0;
    NotebookLanguage language = NotebookLanguage::en;
    std::string description;
};
```

- **Purpose**: Metadata describing one group of related terms in the notebook DB.
- **Fields**:
  - `id` – Primary key for the group.
  - `language` – Language for the entire group (`zh` or `en`).
  - `description` – Human-friendly label for the group (e.g., `"happy, joyful, glad"`).


### 2.5 `SynonymTerm` (`synonym_term.h`)

```cpp
class SynonymTerm {
  public:
    int id = 0;
    int set_id = 0;
    std::string term_text;
    std::string normalized_text;
};
```

- **Purpose**: Represents a single word/phrase in a synonym set.
- **Fields**:
  - `id` – Primary key for this term.
  - `set_id` – Foreign key pointing to `SynonymSet::id`.
  - `term_text` – Original token as it appears in CSV / user input.
  - `normalized_text` – Canonicalized version used for fast joins and search.


3. Legacy Thesaurus Graph
-------------------------

### 3.1 `aiThesaurusWord` (`ai_thesaurus_word.h` / `ai_thesaurus_word.cpp`)

```cpp
class aiThesaurusWord {
    friend class wordsDictionary;

  protected:
    std::set<aiThesaurusWord *> aiWordSynonyms;
    std::set<aiThesaurusWord *> aiWordTranslations;

  public:
    const std::string word;
    LegacyLanguage language;

    aiThesaurusWord(const std::string &queryWord, LegacyLanguage queryLanguage);
};
```

**Role**: Node in the legacy thesaurus graph. Each word (in Chinese or English) is represented by one `aiThesaurusWord` instance.

**Fields**:

- `word` – Canonical spelling of this word.
- `language` – Which language bucket it belongs to (`LegacyLanguage::chinese` or `LegacyLanguage::english`).
- `aiWordSynonyms` (protected) – Set of pointers to synonym nodes in the same language.
- `aiWordTranslations` (protected) – Set of pointers to cross-language translation nodes.

**Constructor**:

```cpp
aiThesaurusWord::aiThesaurusWord(const std::string &queryWord,
                                 LegacyLanguage queryLanguage)
    : word{queryWord},
      language{queryLanguage},
      aiWordSynonyms{},
      aiWordTranslations{} {}
```

- Stores the word and language.
- Initializes synonym/translation sets empty; they are later filled by `wordsDictionary`.

**Usage**:

- `wordsDictionary` creates and stores these nodes in its `database` maps.
- It then wires edges by inserting pointers into `aiWordSynonyms` and `aiWordTranslations`.


### 3.2 `wordsDictionary` (`words_dictionary.h` / `words_dictionary.cpp`)

```cpp
class wordsDictionary {
  private:
    std::map<std::string, aiThesaurusWord *> database;
    std::map<std::string, aiThesaurusWord *> ZHDatabase;
    std::map<std::string, aiThesaurusWord *> ENDatabase;

    wordsDictionary();

    void createAllChineseSynonyms();
    void createAllEnglishSynonyms();
    void createAllTranslations();

    std::unique_ptr<std::ifstream> loadChineseSynonymFile();
    std::unique_ptr<std::ifstream> loadEnglishSynonymFile();
    std::unique_ptr<std::ifstream> loadTranslationFile();

    bool getTokens(std::istringstream &iss, std::string &token);

  public:
    void initializeChineseSynonyms();
    void initializeEnglishSynonyms();
    void initializeTranslations();
};
```

**Role**: High-level manager that builds and owns the entire legacy thesaurus graph.

**Fields**:

- `database` – Master map: string → `aiThesaurusWord*` for all words.
- `ZHDatabase` – Subset for Chinese words.
- `ENDatabase` – Subset for English words.

**Constructor**:

- Calls, in order:
  - `createAllChineseSynonyms()` – Pass 1: create Chinese nodes.
  - `createAllEnglishSynonyms()` – Pass 1: create English nodes.
  - `createAllTranslations()` – Pass 1: create any missing nodes from translation CSV.
  - `initializeChineseSynonyms()` – Pass 2: connect Chinese synonym edges.
  - `initializeEnglishSynonyms()` – Pass 2: connect English synonym edges.
  - (Translation edges planned in `initializeTranslations()`).

**Private helpers**:

- `loadChineseSynonymFile()` – Opens `cn_thesaurus.txt` and returns `unique_ptr<ifstream>`.
- `loadEnglishSynonymFile()` – Opens `WordnetThesaurus.csv`.
- `loadTranslationFile()` – Opens `ecdict.csv`.
- `getTokens(iss, token)` – Reads comma-separated tokens using `getline(iss, token, ',')`.

**Creation passes**:

- `createAllChineseSynonyms()`:
  - Loops over each line of `cn_thesaurus.txt`.
  - Splits by comma via `getTokens`, trims whitespace.
  - For each token, if not in `database`, creates a new `aiThesaurusWord(token, LegacyLanguage::chinese)` and inserts into `database` and `ZHDatabase`.

- `createAllEnglishSynonyms()`:
  - Similar to the Chinese version, but reading `WordnetThesaurus.csv` and storing words as `LegacyLanguage::english`.

- `createAllTranslations()`:
  - Reads `ecdict.csv`, skipping the header row.
  - For the important columns (index 0, 3), ensures English and Chinese words exist in `database`, `ENDatabase`, `ZHDatabase`.
  - Intended later to also wire `aiWordTranslations` edges.

**Initialization passes**:

- `initializeChineseSynonyms()`:
  - Re-scans `cn_thesaurus.txt`.
  - For each non-empty line:
    - Splits into `tokens` (synonyms in one group).
    - For each pair `(headword, synonym)` in that line:
      - Adds `database[headword]->aiWordSynonyms.emplace(database[synonym]);`
        (the current code uses `emplace(tokens[idxSynonym])` and should be updated to store pointers, not strings).

- `initializeEnglishSynonyms()`:
  - Same pattern as `initializeChineseSynonyms()`, but using the English file.

- `initializeTranslations()`:
  - Currently a stub; final design should loop over `ecdict.csv` rows and, for matching English/Chinese words, add pointers into each node’s `aiWordTranslations`.


4. Language-Specific Thesaurus Nodes
------------------------------------

### 4.1 `enAiThesaurusWord` (`en_ai_thesaurus_word.h` / `en_ai_thesaurus_word.cpp`)

```cpp
class enAiThesaurusWord : public aiThesaurusWord {
  public:
    explicit enAiThesaurusWord(const std::string &queryWord);
};
```

**Role**: English-specific subclass of `aiThesaurusWord`. It currently only sets `language` to English but provides a place to add English-specific behavior later (stemming, British/American spelling normalization, etc.).

**Constructor**:

```cpp
enAiThesaurusWord::enAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::english} {}
```


### 4.2 `zhAiThesaurusWord` (`zh_ai_thesaurus_word.h` / `zh_ai_thesaurus_word.cpp`)

```cpp
class zhAiThesaurusWord : public aiThesaurusWord {
  protected:
    virtual bool getTokens(std::istringstream &iss, std::string &token);
    virtual std::string getExportName() const;

  public:
    zhAiThesaurusWord(const std::string &queryWord);
    virtual std::unique_ptr<std::ifstream> loadFile();
    std::set<std::string> getSynonyms(const std::string &word);
    void printAll() const;
    void exportAll() const;
};
```

**Intended role**: Chinese-specialized thesaurus word helper. It provides:

- Custom token parsing for Chinese synonym lines.
- A way to load the Chinese thesaurus file.
- Convenience methods for querying and exporting Chinese synonym data.

**Fields (inherited)**:

- `word` – The Chinese word string.
- `language` – Should be `LegacyLanguage::chinese`.
- `aiWordSynonyms` / `aiWordTranslations` – Edges in the graph.

**Constructor**:

```cpp
zhAiThesaurusWord::zhAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::chinese} {}
```

(The current file uses `LegacyLanguage::english`; this should be updated to `LegacyLanguage::chinese`.)

**Protected methods**:

- `bool getTokens(std::istringstream &iss, std::string &token);`
  - Implementation plan:
    - Use `iss >> token` to split by any whitespace and avoid empty tokens.
    - If later needed, extend it to handle Chinese punctuation separators (`，`, `、`, etc.).
  - Returns `true` when a new token is read; `false` when there is no more data.

- `std::string getExportName() const;`
  - Returns a descriptive label for export operations, e.g. `"Chinese Thesaurus"`.
  - Used by `printAll()` / `exportAll()` to write headers or file names.

**Public methods**:

- `std::unique_ptr<std::ifstream> loadFile();`
  - Opens and returns a stream to the Chinese synonym file:
    - `return std::make_unique<std::ifstream>("Unchanged-Databases\\Chinese_Thesaurus\\cn_thesaurus.txt");`
  - Callers can then read lines and parse them using `getTokens()`.

- `std::set<std::string> getSynonyms(const std::string &word);`
  - Looks up a Chinese word in the dictionary graph, then:
    - Reads the `aiWordSynonyms` set connected to that node.
    - Returns a `std::set<std::string>` with all unique synonym spellings.
  - This method assumes the `wordsDictionary` (or another manager) has already populated the graph.

- `void printAll() const;`
  - Iterates over all Chinese nodes and prints each synonym group for debugging.
  - Intended behavior:
    - For each headword: print the word followed by its synonyms from `aiWordSynonyms`.
    - Use `getExportName()` for an introductory header like `"Chinese Thesaurus (debug output)"`.

- `void exportAll() const;`
  - Exports every synonym group to disk.
  - Intended behavior:
    - Open an output file (e.g., `"chinese_thesaurus_export.csv"`).
    - For each headword, gather its synonyms and write one line per group.
    - Use `getExportName()` to name or label the export.

In summary, `zhAiThesaurusWord` is the Chinese-aware convenience wrapper around `aiThesaurusWord`: it knows how to read the Chinese thesaurus file, how to tokenize lines, how to query synonyms, and how to export them in a friendly way.


5. Legacy Thesaurus Adapter
---------------------------

### 5.1 `LegacyThesaurusAdapter` (`legacy_thesaurus_adapter.h`)

```cpp
class LegacyThesaurusAdapter {
  public:
    wordsDictionary build_dictionary(LegacyLanguage language);
    wordsDictionary load_from_header_sources();
    void export_synonym_groups(const wordsDictionary &dict);
};
```

**Role**: Bridges the legacy C++ thesaurus graph into the modern notebook world.

**Methods**:

- `wordsDictionary build_dictionary(LegacyLanguage language);`
  - Constructs a `wordsDictionary` instance and prepares it for the requested language.
  - Likely used by a higher-level script or tool to generate exports for either Chinese or English.

- `wordsDictionary load_from_header_sources();`
  - Helper that instantiates `wordsDictionary` using the current header/source files.
  - Ensures that all initialization passes (`createAll*` and `initialize*`) have been run.

- `void export_synonym_groups(const wordsDictionary &dict);`
  - Walks the `wordsDictionary` graph and emits data in a form that another layer can import into SQLite (for example, CSV files listing groups and terms).


6. Modern Notebook / Search Abstractions
----------------------------------------

### 6.1 `VocabularyRepository` (`vocabulary_repository.h`)

```cpp
class VocabularyRepository {
  public:
    virtual ~VocabularyRepository() = default;
    virtual void connect(const std::string &db_path) = 0;
    virtual void insert_entry(const VocabularyEntry &entry) = 0;
    virtual void bulk_insert(const std::vector<VocabularyEntry> &entries) = 0;
    virtual void attach_synonym(int vocab_id,
                                int term_id,
                                const std::string &kind,
                                double score) = 0;
    virtual std::vector<VocabularyEntry>
    search_by_terms(const std::set<std::string> &terms,
                    NotebookLanguage language) = 0;
    virtual std::set<SynonymTerm>
    fetch_synonyms(const std::string &normalized,
                   NotebookLanguage language) = 0;
};
```

**Role**: Thin data-access layer around the SQLite DB.

**Methods**:

- `connect(db_path)` – Open a connection to the database file on disk.
- `insert_entry(entry)` – Insert or update a single `VocabularyEntry`.
- `bulk_insert(entries)` – Batch insert many entries for performance.
- `attach_synonym(vocab_id, term_id, kind, score)` – Record a link between a vocab entry and a synonym term, with a `kind` label and numeric `score`.
- `search_by_terms(terms, language)` – Return every `VocabularyEntry` that matches any of the normalized terms.
- `fetch_synonyms(normalized, language)` – Return all `SynonymTerm`s that match the normalized token.


### 6.2 `CsvImporter` (`csv_importer.h`)

```cpp
class CsvImporter {
  public:
    virtual ~CsvImporter() = default;
    virtual void import_translation_csv(const std::string &path,
                                        VocabularyRepository &repo,
                                        int batch_id) = 0;
    virtual void import_user_vocab(const std::string &path,
                                   VocabularyRepository &repo) = 0;
};
```

**Role**: Handles CSV ingestion for translations and user vocabulary.

**Methods**:

- `import_translation_csv(path, repo, batch_id)` – Reads a translation CSV, normalizes rows, and writes them into the repository with a given batch identifier.
- `import_user_vocab(path, repo)` – Imports user-created vocabulary CSV files into the database.


### 6.3 `SearchService` (`search_service.h`)

```cpp
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
```

**Role**: High-level API powering the desktop search box.

**Methods**:

- `search_vocabulary(...)`:
  - 1) Uses `collect_candidate_terms()` to expand the query into normalized tokens and synonyms.
  - 2) Asks `VocabularyRepository` for matching entries.
  - 3) Calls `rank_results()` to sort the entries by relevance using `FuzzyMatcher`.
  - 4) Returns a ranked list of `VocabularyEntry` objects.

- `collect_candidate_terms(...)`:
  - Normalizes the query text via `TextNormalizer`.
  - Uses `SynonymResolver` to expand the query into related terms (synonyms, linked vocab).
  - Returns the union of all candidate tokens.

- `rank_results(...)`:
  - Calculates relevance scores using `FuzzyMatcher::distance` / `similarity`.
  - Sorts and filters the results for the best matches.


### 6.4 `SynonymResolver` (`synonym_resolver.h`)

```cpp
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
```

**Role**: Expands user queries into larger synonym sets before searching.

**Methods**:

- `get_related_terms(query, language, repo)` – Given a normalized token, finds synonyms in the database and returns a set of related terms.
- `expand_with_linked_vocab(terms, language, repo)` – Given a set of terms, walks the vocabulary/synonym links in the DB to add more related tokens and returns the expanded set.


### 6.5 `TextNormalizer` (`text_normalizer.h`)

```cpp
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
```

**Role**: Provides reusable text normalization helpers.

**Methods**:

- `normalize(text, language)` – High-level normalization pipeline (calls the other helpers as appropriate).
- `strip_punctuation(text)` – Removes punctuation.
- `canonicalize_width(text)` – Normalizes full-width and half-width characters.
- `to_lower_ascii(text)` – Lowercases ASCII and standardizes casing.
- `simplify_chinese(text)` – Optionally converts traditional → simplified Chinese so matching is more consistent.


### 6.6 `FuzzyMatcher` (`fuzzy_matcher.h`)

```cpp
class FuzzyMatcher {
  public:
    virtual ~FuzzyMatcher() = default;

    virtual int distance(const std::string &a, const std::string &b) const = 0;
    virtual double similarity(const std::string &a, const std::string &b) const = 0;
    virtual bool is_close(const std::string &a,
                          const std::string &b,
                          double threshold) const = 0;
};
```

**Role**: Abstract interface for Levenshtein/ratio-based similarity checks.

**Methods**:

- `distance(a, b)` – Returns an edit distance or similar metric.
- `similarity(a, b)` – Returns a similarity score (e.g., 0.0 – 1.0).
- `is_close(a, b, threshold)` – Returns `true` if similarity exceeds the given threshold.


7. End-to-End Workflow
----------------------

Putting it all together, the intended end-to-end flow looks like this:

1. **Legacy graph construction**  
   - `LegacyThesaurusAdapter` creates a `wordsDictionary`.
   - The `wordsDictionary` constructor:
     - Reads Chinese/English thesaurus files and translation CSV.
     - Builds `aiThesaurusWord` nodes and fills `database`, `ZHDatabase`, `ENDatabase`.
     - Calls `initializeChineseSynonyms()` and `initializeEnglishSynonyms()` to wire synonym edges.
     - (Future step) Calls `initializeTranslations()` to wire translation edges.

2. **Legacy export to notebook**  
   - `LegacyThesaurusAdapter::export_synonym_groups(dict)`:
     - Walks each node and its synonym groups.
     - Writes out CSV files or calls a Python process that inserts `SynonymSet` and `SynonymTerm` records into SQLite via a `VocabularyRepository` implementation.

3. **Importing into SQLite**  
   - `CsvImporter` reads exported synonym CSVs and user vocabulary CSVs.
   - It normalizes text with `TextNormalizer` and inserts data into SQLite using `VocabularyRepository`.

4. **Interactive search**  
   - A UI or CLI calls `SearchService::search_vocabulary(query_text, language, repo, resolver, normalizer, matcher)`.
   - The `SearchService`:
     - Normalizes text via `TextNormalizer`.
     - Expands terms via `SynonymResolver` (`get_related_terms`, `expand_with_linked_vocab`).
     - Queries `VocabularyRepository::search_by_terms`.
     - Ranks results using `FuzzyMatcher` (`distance`, `similarity`, `is_close`).
   - Returns a ranked list of `VocabularyEntry` records for the UI to show.


8. Next Steps / Implementation Plan
-----------------------------------

Here is a concrete plan for evolving the project using this design:

1. **Fix and complete `zhAiThesaurusWord`**  
   - Set its constructor to use `LegacyLanguage::chinese`.  
   - Implement `loadFile()` to open `cn_thesaurus.txt`.  
   - Add implementations for `getSynonyms`, `printAll`, and `exportAll` that traverse the `wordsDictionary` graph.

2. **Refine `wordsDictionary` edges**  
   - Update `initializeChineseSynonyms()` and `initializeEnglishSynonyms()` to store pointers in `aiWordSynonyms` instead of raw strings.  
   - Implement `initializeTranslations()` to connect `aiWordTranslations`.

3. **Finish `LegacyThesaurusAdapter`**  
   - Implement `build_dictionary` and `load_from_header_sources`.  
   - Implement `export_synonym_groups` to output a stable CSV format for the notebook.

4. **Implement concrete notebook/search classes**  
   - Create concrete `VocabularyRepository` backed by SQLite.  
   - Implement `TextNormalizer`, `SynonymResolver`, `FuzzyMatcher`, and `SearchService` using the interfaces defined here.

5. **Wire up CLI or tests**  
   - Add a small CLI or test harness that:
     - Builds the legacy graph.
     - Exports synonym groups.
     - Imports them into SQLite.
     - Runs sample search queries (both English and Chinese) against the `SearchService`.

With this structure, you can confidently extend the system: the legacy graph stays isolated in a small part of the code, while everything else talks to clean interfaces (`VocabularyRepository`, `SearchService`, `CsvImporter`, etc.).

=======
AI_VOCAB_NOTEBOOK – Project Design Overview
===========================================

This document explains the overall plan for the project, with a focus on:

- What each major class represents.
- The meaning of every field and method in the C++ headers under `c++-file-new/header-files-new`.
- How data flows from the legacy thesaurus files into the modern notebook/search stack.
- Where `zhAiThesaurusWord` fits into the design.

The goal is to give you a clear mental model so you can extend or refactor the code confidently.


1. High-Level Architecture
--------------------------

The project has two “layers”:

1. **Legacy thesaurus layer (C++ in this repo)**  
   - Works with raw text files:
     - `Unchanged-Databases/Chinese_Thesaurus/cn_thesaurus.txt`
     - `Unchanged-Databases/English_Thesaurus/WordnetThesaurus.csv`
     - `Unchanged-Databases/Translation_Dictionary/ecdict.csv`
   - Builds an in-memory graph of words and edges (synonyms and translations).
   - `wordsDictionary` and `aiThesaurusWord` are the core of this layer.

2. **Modern notebook/search layer (SQLite + abstractions)**  
   - Uses a normalized vocabulary database (SQLite) with tables like vocabulary entries, synonym sets, synonym terms, and links.
   - Adds search and fuzzy matching on top.
   - Classes like `VocabularyEntry`, `VocabularyRepository`, `SearchService`, `SynonymResolver`, `TextNormalizer`, `FuzzyMatcher`, `CsvImporter` live here.

`LegacyThesaurusAdapter` is the bridge between these two worlds: it builds the legacy graph, then exports the data into a form the notebook/search layer can consume.


2. Core Enums and Basic Data Types
----------------------------------

### 2.1 `LegacyLanguage` (`enums.h`)

```cpp
enum LegacyLanguage {
    chinese,
    english
};
```

- **Purpose**: Identifies which language a legacy thesaurus word belongs to.
- **Values**:
  - `chinese` – Simplified Chinese entries from `cn_thesaurus.txt` or translation CSV.
  - `english` – English entries from WordNet or translation CSV.

Used by: `aiThesaurusWord`, `wordsDictionary`, `LegacyThesaurusAdapter`.


### 2.2 `NotebookLanguage` (`notebook_language.h`)

```cpp
enum class NotebookLanguage {
    zh,
    en
};
```

- **Purpose**: Language flag used by the modern notebook/search stack.
- **Values**:
  - `NotebookLanguage::zh` – Chinese.
  - `NotebookLanguage::en` – English.

Used by: `SearchService`, `VocabularyRepository`, `SynonymSet`, `SynonymResolver`, `TextNormalizer`.


### 2.3 `VocabularyEntry` (`vocabulary_entry.h`)

```cpp
class VocabularyEntry {
  public:
    int id = 0;
    std::string chinese_text;
    std::string english_text;
    std::string part_of_speech;
    std::vector<std::string> tags;
    std::string notes;
    std::string created_at;
    std::string updated_at;
};
```

- **Purpose**: In-memory representation of a single row in the user’s vocabulary table.
- **Fields**:
  - `id` – Primary key from SQLite.
  - `chinese_text` – The Chinese side of the vocabulary pair.
  - `english_text` – The English side.
  - `part_of_speech` – POS tag, e.g. `"noun"`, `"verb"`.
  - `tags` – Arbitrary labels to group entries (e.g., `"HSK3"`, `"work"`).
  - `notes` – Free-form user notes.
  - `created_at` / `updated_at` – Timestamps as strings (e.g., ISO 8601).


### 2.4 `SynonymSet` (`synonym_set.h`)

```cpp
class SynonymSet {
  public:
    int id = 0;
    NotebookLanguage language = NotebookLanguage::en;
    std::string description;
};
```

- **Purpose**: Metadata describing one group of related terms in the notebook DB.
- **Fields**:
  - `id` – Primary key for the group.
  - `language` – Language for the entire group (`zh` or `en`).
  - `description` – Human-friendly label for the group (e.g., `"happy, joyful, glad"`).


### 2.5 `SynonymTerm` (`synonym_term.h`)

```cpp
class SynonymTerm {
  public:
    int id = 0;
    int set_id = 0;
    std::string term_text;
    std::string normalized_text;
};
```

- **Purpose**: Represents a single word/phrase in a synonym set.
- **Fields**:
  - `id` – Primary key for this term.
  - `set_id` – Foreign key pointing to `SynonymSet::id`.
  - `term_text` – Original token as it appears in CSV / user input.
  - `normalized_text` – Canonicalized version used for fast joins and search.


3. Legacy Thesaurus Graph
-------------------------

### 3.1 `aiThesaurusWord` (`ai_thesaurus_word.h` / `ai_thesaurus_word.cpp`)

```cpp
class aiThesaurusWord {
    friend class wordsDictionary;

  protected:
    std::set<aiThesaurusWord *> aiWordSynonyms;
    std::set<aiThesaurusWord *> aiWordTranslations;

  public:
    const std::string word;
    LegacyLanguage language;

    aiThesaurusWord(const std::string &queryWord, LegacyLanguage queryLanguage);
};
```

**Role**: Node in the legacy thesaurus graph. Each word (in Chinese or English) is represented by one `aiThesaurusWord` instance.

**Fields**:

- `word` – Canonical spelling of this word.
- `language` – Which language bucket it belongs to (`LegacyLanguage::chinese` or `LegacyLanguage::english`).
- `aiWordSynonyms` (protected) – Set of pointers to synonym nodes in the same language.
- `aiWordTranslations` (protected) – Set of pointers to cross-language translation nodes.

**Constructor**:

```cpp
aiThesaurusWord::aiThesaurusWord(const std::string &queryWord,
                                 LegacyLanguage queryLanguage)
    : word{queryWord},
      language{queryLanguage},
      aiWordSynonyms{},
      aiWordTranslations{} {}
```

- Stores the word and language.
- Initializes synonym/translation sets empty; they are later filled by `wordsDictionary`.

**Usage**:

- `wordsDictionary` creates and stores these nodes in its `database` maps.
- It then wires edges by inserting pointers into `aiWordSynonyms` and `aiWordTranslations`.


### 3.2 `wordsDictionary` (`words_dictionary.h` / `words_dictionary.cpp`)

```cpp
class wordsDictionary {
  private:
    std::map<std::string, aiThesaurusWord *> database;
    std::map<std::string, aiThesaurusWord *> ZHDatabase;
    std::map<std::string, aiThesaurusWord *> ENDatabase;

    wordsDictionary();

    void createAllChineseSynonyms();
    void createAllEnglishSynonyms();
    void createAllTranslations();

    std::unique_ptr<std::ifstream> loadChineseSynonymFile();
    std::unique_ptr<std::ifstream> loadEnglishSynonymFile();
    std::unique_ptr<std::ifstream> loadTranslationFile();

    bool getTokens(std::istringstream &iss, std::string &token);

  public:
    void initializeChineseSynonyms();
    void initializeEnglishSynonyms();
    void initializeTranslations();
};
```

**Role**: High-level manager that builds and owns the entire legacy thesaurus graph.

**Fields**:

- `database` – Master map: string → `aiThesaurusWord*` for all words.
- `ZHDatabase` – Subset for Chinese words.
- `ENDatabase` – Subset for English words.

**Constructor**:

- Calls, in order:
  - `createAllChineseSynonyms()` – Pass 1: create Chinese nodes.
  - `createAllEnglishSynonyms()` – Pass 1: create English nodes.
  - `createAllTranslations()` – Pass 1: create any missing nodes from translation CSV.
  - `initializeChineseSynonyms()` – Pass 2: connect Chinese synonym edges.
  - `initializeEnglishSynonyms()` – Pass 2: connect English synonym edges.
  - (Translation edges planned in `initializeTranslations()`).

**Private helpers**:

- `loadChineseSynonymFile()` – Opens `cn_thesaurus.txt` and returns `unique_ptr<ifstream>`.
- `loadEnglishSynonymFile()` – Opens `WordnetThesaurus.csv`.
- `loadTranslationFile()` – Opens `ecdict.csv`.
- `getTokens(iss, token)` – Reads comma-separated tokens using `getline(iss, token, ',')`.

**Creation passes**:

- `createAllChineseSynonyms()`:
  - Loops over each line of `cn_thesaurus.txt`.
  - Splits by comma via `getTokens`, trims whitespace.
  - For each token, if not in `database`, creates a new `aiThesaurusWord(token, LegacyLanguage::chinese)` and inserts into `database` and `ZHDatabase`.

- `createAllEnglishSynonyms()`:
  - Similar to the Chinese version, but reading `WordnetThesaurus.csv` and storing words as `LegacyLanguage::english`.

- `createAllTranslations()`:
  - Reads `ecdict.csv`, skipping the header row.
  - For the important columns (index 0, 3), ensures English and Chinese words exist in `database`, `ENDatabase`, `ZHDatabase`.
  - Intended later to also wire `aiWordTranslations` edges.

**Initialization passes**:

- `initializeChineseSynonyms()`:
  - Re-scans `cn_thesaurus.txt`.
  - For each non-empty line:
    - Splits into `tokens` (synonyms in one group).
    - For each pair `(headword, synonym)` in that line:
      - Adds `database[headword]->aiWordSynonyms.emplace(database[synonym]);`
        (the current code uses `emplace(tokens[idxSynonym])` and should be updated to store pointers, not strings).

- `initializeEnglishSynonyms()`:
  - Same pattern as `initializeChineseSynonyms()`, but using the English file.

- `initializeTranslations()`:
  - Currently a stub; final design should loop over `ecdict.csv` rows and, for matching English/Chinese words, add pointers into each node’s `aiWordTranslations`.


4. Language-Specific Thesaurus Nodes
------------------------------------

### 4.1 `enAiThesaurusWord` (`en_ai_thesaurus_word.h` / `en_ai_thesaurus_word.cpp`)

```cpp
class enAiThesaurusWord : public aiThesaurusWord {
  public:
    explicit enAiThesaurusWord(const std::string &queryWord);
};
```

**Role**: English-specific subclass of `aiThesaurusWord`. It currently only sets `language` to English but provides a place to add English-specific behavior later (stemming, British/American spelling normalization, etc.).

**Constructor**:

```cpp
enAiThesaurusWord::enAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::english} {}
```


### 4.2 `zhAiThesaurusWord` (`zh_ai_thesaurus_word.h` / `zh_ai_thesaurus_word.cpp`)

```cpp
class zhAiThesaurusWord : public aiThesaurusWord {
  protected:
    virtual bool getTokens(std::istringstream &iss, std::string &token);
    virtual std::string getExportName() const;

  public:
    zhAiThesaurusWord(const std::string &queryWord);
    virtual std::unique_ptr<std::ifstream> loadFile();
    std::set<std::string> getSynonyms(const std::string &word);
    void printAll() const;
    void exportAll() const;
};
```

**Intended role**: Chinese-specialized thesaurus word helper. It provides:

- Custom token parsing for Chinese synonym lines.
- A way to load the Chinese thesaurus file.
- Convenience methods for querying and exporting Chinese synonym data.

**Fields (inherited)**:

- `word` – The Chinese word string.
- `language` – Should be `LegacyLanguage::chinese`.
- `aiWordSynonyms` / `aiWordTranslations` – Edges in the graph.

**Constructor**:

```cpp
zhAiThesaurusWord::zhAiThesaurusWord(const std::string &queryWord)
    : aiThesaurusWord{queryWord, LegacyLanguage::chinese} {}
```

(The current file uses `LegacyLanguage::english`; this should be updated to `LegacyLanguage::chinese`.)

**Protected methods**:

- `bool getTokens(std::istringstream &iss, std::string &token);`
  - Implementation plan:
    - Use `iss >> token` to split by any whitespace and avoid empty tokens.
    - If later needed, extend it to handle Chinese punctuation separators (`，`, `、`, etc.).
  - Returns `true` when a new token is read; `false` when there is no more data.

- `std::string getExportName() const;`
  - Returns a descriptive label for export operations, e.g. `"Chinese Thesaurus"`.
  - Used by `printAll()` / `exportAll()` to write headers or file names.

**Public methods**:

- `std::unique_ptr<std::ifstream> loadFile();`
  - Opens and returns a stream to the Chinese synonym file:
    - `return std::make_unique<std::ifstream>("Unchanged-Databases\\Chinese_Thesaurus\\cn_thesaurus.txt");`
  - Callers can then read lines and parse them using `getTokens()`.

- `std::set<std::string> getSynonyms(const std::string &word);`
  - Looks up a Chinese word in the dictionary graph, then:
    - Reads the `aiWordSynonyms` set connected to that node.
    - Returns a `std::set<std::string>` with all unique synonym spellings.
  - This method assumes the `wordsDictionary` (or another manager) has already populated the graph.

- `void printAll() const;`
  - Iterates over all Chinese nodes and prints each synonym group for debugging.
  - Intended behavior:
    - For each headword: print the word followed by its synonyms from `aiWordSynonyms`.
    - Use `getExportName()` for an introductory header like `"Chinese Thesaurus (debug output)"`.

- `void exportAll() const;`
  - Exports every synonym group to disk.
  - Intended behavior:
    - Open an output file (e.g., `"chinese_thesaurus_export.csv"`).
    - For each headword, gather its synonyms and write one line per group.
    - Use `getExportName()` to name or label the export.

In summary, `zhAiThesaurusWord` is the Chinese-aware convenience wrapper around `aiThesaurusWord`: it knows how to read the Chinese thesaurus file, how to tokenize lines, how to query synonyms, and how to export them in a friendly way.


5. Legacy Thesaurus Adapter
---------------------------

### 5.1 `LegacyThesaurusAdapter` (`legacy_thesaurus_adapter.h`)

```cpp
class LegacyThesaurusAdapter {
  public:
    wordsDictionary build_dictionary(LegacyLanguage language);
    wordsDictionary load_from_header_sources();
    void export_synonym_groups(const wordsDictionary &dict);
};
```

**Role**: Bridges the legacy C++ thesaurus graph into the modern notebook world.

**Methods**:

- `wordsDictionary build_dictionary(LegacyLanguage language);`
  - Constructs a `wordsDictionary` instance and prepares it for the requested language.
  - Likely used by a higher-level script or tool to generate exports for either Chinese or English.

- `wordsDictionary load_from_header_sources();`
  - Helper that instantiates `wordsDictionary` using the current header/source files.
  - Ensures that all initialization passes (`createAll*` and `initialize*`) have been run.

- `void export_synonym_groups(const wordsDictionary &dict);`
  - Walks the `wordsDictionary` graph and emits data in a form that another layer can import into SQLite (for example, CSV files listing groups and terms).


6. Modern Notebook / Search Abstractions
----------------------------------------

### 6.1 `VocabularyRepository` (`vocabulary_repository.h`)

```cpp
class VocabularyRepository {
  public:
    virtual ~VocabularyRepository() = default;
    virtual void connect(const std::string &db_path) = 0;
    virtual void insert_entry(const VocabularyEntry &entry) = 0;
    virtual void bulk_insert(const std::vector<VocabularyEntry> &entries) = 0;
    virtual void attach_synonym(int vocab_id,
                                int term_id,
                                const std::string &kind,
                                double score) = 0;
    virtual std::vector<VocabularyEntry>
    search_by_terms(const std::set<std::string> &terms,
                    NotebookLanguage language) = 0;
    virtual std::set<SynonymTerm>
    fetch_synonyms(const std::string &normalized,
                   NotebookLanguage language) = 0;
};
```

**Role**: Thin data-access layer around the SQLite DB.

**Methods**:

- `connect(db_path)` – Open a connection to the database file on disk.
- `insert_entry(entry)` – Insert or update a single `VocabularyEntry`.
- `bulk_insert(entries)` – Batch insert many entries for performance.
- `attach_synonym(vocab_id, term_id, kind, score)` – Record a link between a vocab entry and a synonym term, with a `kind` label and numeric `score`.
- `search_by_terms(terms, language)` – Return every `VocabularyEntry` that matches any of the normalized terms.
- `fetch_synonyms(normalized, language)` – Return all `SynonymTerm`s that match the normalized token.


### 6.2 `CsvImporter` (`csv_importer.h`)

```cpp
class CsvImporter {
  public:
    virtual ~CsvImporter() = default;
    virtual void import_translation_csv(const std::string &path,
                                        VocabularyRepository &repo,
                                        int batch_id) = 0;
    virtual void import_user_vocab(const std::string &path,
                                   VocabularyRepository &repo) = 0;
};
```

**Role**: Handles CSV ingestion for translations and user vocabulary.

**Methods**:

- `import_translation_csv(path, repo, batch_id)` – Reads a translation CSV, normalizes rows, and writes them into the repository with a given batch identifier.
- `import_user_vocab(path, repo)` – Imports user-created vocabulary CSV files into the database.


### 6.3 `SearchService` (`search_service.h`)

```cpp
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
```

**Role**: High-level API powering the desktop search box.

**Methods**:

- `search_vocabulary(...)`:
  - 1) Uses `collect_candidate_terms()` to expand the query into normalized tokens and synonyms.
  - 2) Asks `VocabularyRepository` for matching entries.
  - 3) Calls `rank_results()` to sort the entries by relevance using `FuzzyMatcher`.
  - 4) Returns a ranked list of `VocabularyEntry` objects.

- `collect_candidate_terms(...)`:
  - Normalizes the query text via `TextNormalizer`.
  - Uses `SynonymResolver` to expand the query into related terms (synonyms, linked vocab).
  - Returns the union of all candidate tokens.

- `rank_results(...)`:
  - Calculates relevance scores using `FuzzyMatcher::distance` / `similarity`.
  - Sorts and filters the results for the best matches.


### 6.4 `SynonymResolver` (`synonym_resolver.h`)

```cpp
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
```

**Role**: Expands user queries into larger synonym sets before searching.

**Methods**:

- `get_related_terms(query, language, repo)` – Given a normalized token, finds synonyms in the database and returns a set of related terms.
- `expand_with_linked_vocab(terms, language, repo)` – Given a set of terms, walks the vocabulary/synonym links in the DB to add more related tokens and returns the expanded set.


### 6.5 `TextNormalizer` (`text_normalizer.h`)

```cpp
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
```

**Role**: Provides reusable text normalization helpers.

**Methods**:

- `normalize(text, language)` – High-level normalization pipeline (calls the other helpers as appropriate).
- `strip_punctuation(text)` – Removes punctuation.
- `canonicalize_width(text)` – Normalizes full-width and half-width characters.
- `to_lower_ascii(text)` – Lowercases ASCII and standardizes casing.
- `simplify_chinese(text)` – Optionally converts traditional → simplified Chinese so matching is more consistent.


### 6.6 `FuzzyMatcher` (`fuzzy_matcher.h`)

```cpp
class FuzzyMatcher {
  public:
    virtual ~FuzzyMatcher() = default;

    virtual int distance(const std::string &a, const std::string &b) const = 0;
    virtual double similarity(const std::string &a, const std::string &b) const = 0;
    virtual bool is_close(const std::string &a,
                          const std::string &b,
                          double threshold) const = 0;
};
```

**Role**: Abstract interface for Levenshtein/ratio-based similarity checks.

**Methods**:

- `distance(a, b)` – Returns an edit distance or similar metric.
- `similarity(a, b)` – Returns a similarity score (e.g., 0.0 – 1.0).
- `is_close(a, b, threshold)` – Returns `true` if similarity exceeds the given threshold.


7. End-to-End Workflow
----------------------

Putting it all together, the intended end-to-end flow looks like this:

1. **Legacy graph construction**  
   - `LegacyThesaurusAdapter` creates a `wordsDictionary`.
   - The `wordsDictionary` constructor:
     - Reads Chinese/English thesaurus files and translation CSV.
     - Builds `aiThesaurusWord` nodes and fills `database`, `ZHDatabase`, `ENDatabase`.
     - Calls `initializeChineseSynonyms()` and `initializeEnglishSynonyms()` to wire synonym edges.
     - (Future step) Calls `initializeTranslations()` to wire translation edges.

2. **Legacy export to notebook**  
   - `LegacyThesaurusAdapter::export_synonym_groups(dict)`:
     - Walks each node and its synonym groups.
     - Writes out CSV files or calls a Python process that inserts `SynonymSet` and `SynonymTerm` records into SQLite via a `VocabularyRepository` implementation.

3. **Importing into SQLite**  
   - `CsvImporter` reads exported synonym CSVs and user vocabulary CSVs.
   - It normalizes text with `TextNormalizer` and inserts data into SQLite using `VocabularyRepository`.

4. **Interactive search**  
   - A UI or CLI calls `SearchService::search_vocabulary(query_text, language, repo, resolver, normalizer, matcher)`.
   - The `SearchService`:
     - Normalizes text via `TextNormalizer`.
     - Expands terms via `SynonymResolver` (`get_related_terms`, `expand_with_linked_vocab`).
     - Queries `VocabularyRepository::search_by_terms`.
     - Ranks results using `FuzzyMatcher` (`distance`, `similarity`, `is_close`).
   - Returns a ranked list of `VocabularyEntry` records for the UI to show.


8. Next Steps / Implementation Plan
-----------------------------------

Here is a concrete plan for evolving the project using this design:

1. **Fix and complete `zhAiThesaurusWord`**  
   - Set its constructor to use `LegacyLanguage::chinese`.  
   - Implement `loadFile()` to open `cn_thesaurus.txt`.  
   - Add implementations for `getSynonyms`, `printAll`, and `exportAll` that traverse the `wordsDictionary` graph.

2. **Refine `wordsDictionary` edges**  
   - Update `initializeChineseSynonyms()` and `initializeEnglishSynonyms()` to store pointers in `aiWordSynonyms` instead of raw strings.  
   - Implement `initializeTranslations()` to connect `aiWordTranslations`.

3. **Finish `LegacyThesaurusAdapter`**  
   - Implement `build_dictionary` and `load_from_header_sources`.  
   - Implement `export_synonym_groups` to output a stable CSV format for the notebook.

4. **Implement concrete notebook/search classes**  
   - Create concrete `VocabularyRepository` backed by SQLite.  
   - Implement `TextNormalizer`, `SynonymResolver`, `FuzzyMatcher`, and `SearchService` using the interfaces defined here.

5. **Wire up CLI or tests**  
   - Add a small CLI or test harness that:
     - Builds the legacy graph.
     - Exports synonym groups.
     - Imports them into SQLite.
     - Runs sample search queries (both English and Chinese) against the `SearchService`.

With this structure, you can confidently extend the system: the legacy graph stays isolated in a small part of the code, while everything else talks to clean interfaces (`VocabularyRepository`, `SearchService`, `CsvImporter`, etc.).

>>>>>>> 792df40 (lasdfsa)
