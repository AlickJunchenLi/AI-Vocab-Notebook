#include "..\\header-files\\noteBook.h"
#include <iostream>
#include <vector>
#include <sstream>
#include <fstream>
#include <string>
#include <map>
#include <set>

using namespace std;

NoteBook::NoteBook(): noteBookSet{{}} {}


void NoteBook::addNote(const map<string, string>& note) {
            noteBookSet.emplace(note);
            return;
}

void NoteBook::displayNotes() const {
        for (const auto& note : noteBookSet) {
            for (const auto& [key, value] : note) {
                cout << key << ": " << value << " | ";
            }
            cout << endl;
        }
    return;
}