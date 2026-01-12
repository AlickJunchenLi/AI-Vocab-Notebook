#ifndef NOTEBOOK_H
#define NOTEBOOK_H

#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <fstream>
#include <sstream>
#include <filesystem>

using namespace std;
class NoteBook {
    protected:
        set < map <string, string> > noteBookSet;
    
    public:
        NoteBook();

        void addNote(const map<string, string>& note);

        void displayNotes() const;
};


#endif // NOTEBOOK_H