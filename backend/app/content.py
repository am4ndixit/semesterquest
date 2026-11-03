"""Starter learning map and practice set. Replace or extend these from faculty uploads."""
WORLDS = [
    {
        "slug": "maths", "title": "Maths Arcade", "subtitle": "Patterns, numbers & problem solving", "icon": "∑", "position": 1,
        "concepts": [
            {"id":"m01","title":"Number sense","description":"Fractions, decimals, percentages and estimation.","kind":"foundation"},
            {"id":"m02","title":"Algebra basics","description":"Variables, expressions and simplifying terms.","kind":"foundation"},
            {"id":"m03","title":"Linear equations","description":"Solve one-variable equations and check solutions.","kind":"core"},
            {"id":"m04","title":"Sequences & AP","description":"Find common differences, nth terms and sums.","kind":"core"},
            {"id":"m05","title":"Functions & graphs","description":"Inputs, outputs, domain, range and graph reading.","kind":"core"},
            {"id":"m06","title":"Logic & sets","description":"Statements, set operations and Venn diagrams.","kind":"challenge"},
        ],
    },
    {
        "slug": "sai", "title": "System & AI Essentials", "subtitle": "Understand the machine under the hood", "icon": "⌘", "position": 2,
        "concepts": [
            {"id":"s01","title":"Computer foundations","description":"IPOS, hardware, software and computer types.","kind":"foundation"},
            {"id":"s02","title":"Operating systems","description":"Processes, memory, devices and file systems.","kind":"core"},
            {"id":"s03","title":"CLI & terminal","description":"Navigate files, use pipes, flags and redirection.","kind":"core"},
            {"id":"s04","title":"Permissions & PATH","description":"Users, ownership, executable permissions and PATH.","kind":"core"},
            {"id":"s05","title":"Number systems","description":"Convert decimal, binary and hexadecimal values.","kind":"core"},
            {"id":"s06","title":"Git & collaboration","description":"Commits, branches, remotes and pull requests.","kind":"challenge"},
            {"id":"s07","title":"Interfaces & APIs","description":"CLI, GUI, APIs, compilers and interpreters.","kind":"challenge"},
        ],
    },
    {
        "slug": "psp", "title": "Python Quest", "subtitle": "Turn logic into working code", "icon": "{ }", "position": 3,
        "concepts": [
            {"id":"p01","title":"Variables & types","description":"Names, integers, floats, strings and booleans.","kind":"foundation"},
            {"id":"p02","title":"Input & output","description":"input(), print(), split(), map() and formatting.","kind":"foundation"},
            {"id":"p03","title":"Operators","description":"Arithmetic, comparison, logical operators and precedence.","kind":"core"},
            {"id":"p04","title":"Conditionals","description":"if, elif, else and nested decisions.","kind":"core"},
            {"id":"p05","title":"Loops","description":"for, range(), while and loop control.","kind":"core"},
            {"id":"p06","title":"Functions","description":"Parameters, return values and scope.","kind":"core"},
            {"id":"p07","title":"Recursion","description":"Base cases, recursive calls and tracing.","kind":"challenge"},
        ],
    },
]

QUESTIONS = [
    ("maths","Sequences & AP","The first term of an AP is 4 and the common difference is 3. What is the 5th term?",["13","16","19","20"],1,"Use aₙ = a + (n − 1)d = 4 + 4×3 = 16.","easy"),
    ("maths","Linear equations","Solve 3x + 5 = 20.",["3","5","7","8"],1,"Subtract 5 to get 3x = 15, then divide by 3.","easy"),
    ("maths","Number sense","What is 15% of 200?",["15","20","30","35"],2,"10% is 20 and 5% is 10, so 15% is 30.","easy"),
    ("maths","Functions & graphs","For f(x) = 2x + 1, what is f(3)?",["5","6","7","8"],2,"Substitute x = 3: 2(3) + 1 = 7.","easy"),
    ("maths","Algebra basics","Simplify 4a + 3a − 2a.",["5a","6a","9a","a"],0,"Combine like terms: (4 + 3 − 2)a = 5a.","easy"),
    ("maths","Logic & sets","If A = {1,2,3} and B = {3,4}, what is A ∩ B?",["{1,2}","{3}","{1,2,3,4}","{4}"],1,"Intersection contains elements present in both sets.","medium"),
    ("sai","Computer foundations","Which sequence best describes the IPOS cycle?",["Input → Process → Output → Storage","Output → Input → Storage → Process","Process → Input → Output → Storage","Input → Output → Process → Storage"],0,"IPOS stands for Input, Process, Output and Storage.","easy"),
    ("sai","Operating systems","Which OS component decides which process gets CPU time?",["File manager","Scheduler","Shell prompt","Compiler"],1,"The scheduler selects a process/thread to run on the CPU.","medium"),
    ("sai","CLI & terminal","What does `pwd` display?",["Current working directory","User password","Running processes","File permissions"],0,"pwd prints the path of the current working directory.","easy"),
    ("sai","CLI & terminal","What does `grep -i error app.log` do?",["Deletes matching lines","Searches case-insensitively for error","Counts all files","Renames app.log"],1,"-i makes grep ignore case while searching for the pattern.","easy"),
    ("sai","Permissions & PATH","What does `chmod +x script.py` do?",["Runs the script","Makes the file executable","Deletes the file","Changes its owner"],1,"The +x permission adds execute permission for applicable user classes.","easy"),
    ("sai","Number systems","What is hexadecimal 3A in decimal?",["48","56","58","62"],2,"3A₁₆ = 3×16 + 10 = 58.","medium"),
    ("sai","Git & collaboration","Which command records staged changes in the local repository?",["git push","git commit","git pull","git clone"],1,"git commit creates a local commit from the staged snapshot.","easy"),
    ("sai","Interfaces & APIs","Which is the best description of an API?",["A physical computer part","A defined way for software systems to communicate","A type of storage drive","A programming language"],1,"An API defines operations and data formats software can use to interact.","easy"),
    ("psp","Variables & types","What is the type of the value returned by input() in Python?",["int","float","str","bool"],2,"input() returns text. Convert it explicitly when you need a number.","easy"),
    ("psp","Input & output","What does `list(map(int, input().split()))` produce?",["A list of integers from space-separated input","A string","A tuple of strings","A single integer"],0,"split() separates tokens, map(int, ...) converts each token, and list collects them.","medium"),
    ("psp","Operators","What is the result of `2 + 3 * 4`?",["20","14","24","18"],1,"Multiplication has higher precedence than addition: 2 + 12 = 14.","easy"),
    ("psp","Conditionals","Which keyword handles the final alternative branch in an if/elif chain?",["otherwise","default","else","finally"],2,"else runs when none of the preceding if/elif conditions is true.","easy"),
    ("psp","Loops","What values does `range(2, 6)` generate?",["2, 3, 4, 5","2, 3, 4, 5, 6","1, 2, 3, 4, 5","3, 4, 5, 6"],0,"The start is included and the stop value is excluded.","easy"),
    ("psp","Functions","What does a Python function send back to its caller with `return`?",["A printed line only","A value","A new variable in every scope","A loop"],1,"return ends the function call and provides a value to the caller.","easy"),
    ("psp","Recursion","What prevents a recursive function from calling itself forever?",["A print statement","A base case","A global variable","A comment"],1,"A base case stops further recursive calls for the simplest input.","easy"),
]
