# Fix Dropdown and Cards Consistency Issues

## Issues to Fix:
1. Dropdown changes width based on available space - needs fixed width
2. Cards resize inconsistently when cards are shown/hidden - need consistent sizing
3. Buttons not aligned - need consistent width and alignment

## Fix Plan:
- [x] Fix dropdown: Set fixed width (300px) instead of 100%
- [x] Fix cards: Use flex display with consistent fixed width (300px), remove flex:1 that causes stretching
- [x] Fix buttons: Make full-width with centered text using flexbox
- [x] Add content-wrapper with min-width: 1000px to prevent container from shrinking when cards are hidden



