# Session Prompts

The prompts used to build this project, starting in Claude Chat and continuing in Claude Code.

---

## Claude Chat

1. My daughter wants to create custom deck for the game Guess Who. I need help coming up with a template to be printed on our home printer, so 8 1/2" x 11" will be the paper size used. I also need a recommendation for the type of paper to use, specifically to be similar to the official Guess Who game. Help me improve this prompt so I can make adjustments.

2. match official card size, 24 unique characters, will use images I provide, include name label for each based on the image filename (minus the extension), include cut guides, each card should have a thin white line border and leave the back blank. let's make this a python script so we can iterate on the changes. the script input can take a path for the images

3. let's move configuration constants to be in a configuration file that can be passed to the script

4. if I do not have the value in the config file, are there defaults in the script?

## Claude Code

5. update generate.py to use 'Bodoni Moda' font

6. let's make the images consistent on height. also add some padding below the text to raise it from the bottom.

7. let's change the card height to be 1 3/8"

8. let's update the background color to be very light gray

9. change it to be light pink. make the text color to be white

10. I mean make the text color to be black

11. make the background color white

12. create an example config called example.config that includes all the configurable settings

13. create a README.md and CLAUDE.md

14. how do I make this a git repository and push to my account?

15. yes [create a .gitignore]

16. make the font default to Helvetica (or whatever is similarly available by default from the OS)

17. we shouldn't have a function specific to a single font. let's make it generic for whatever font is passed in the config

18. update CLAUDE.md and README.md where applicable

19. how do I replace the git remote origin?

20. the remote repo is git@github.com:thenickberry/guess-who-template-generator.git. push it

21. yes go ahead [rebase and push]

22. let's update the output PDF to include two sets each with a corresponding backside page to be the back of the card. this should be ordered so I can do two-sided printing on the same page. use the blue and red examples from this image for the card backside https://whistle-stop.com/wp-content/uploads/2024/04/hasbro_guess-who-card-game_02-1400x513.jpg

23. let's change the image of the backside to be a mix of semi-opaque question marks scattered around in different orientations
