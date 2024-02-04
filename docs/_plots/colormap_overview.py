import matplotlib.pyplot as plt

from fastf1.plotting._constants import Constants


n = len(Constants)  # total number of years

# dynamically adjust figure size depending on number of required subplots
fig = plt.figure(figsize=(10, 3 * n))

# slightly paranoid, sort years explicitly (order is not necessarily
# guaranteed in the internal code)
years_sorted = [str(year) for year in
                sorted((int(year) for year in Constants.keys()), reverse=True)]

# generate one axis/graphic for each year
for i, year in enumerate(years_sorted):
    teams = Constants[year].Teams

    ax = fig.add_subplot(n, 1, i + 1)

    x_labels = list()
    x_ranges = list()
    default_colors = list()
    official_colors = list()

    for j, (name, team) in enumerate(teams.items()):
        x_labels.append(team.ShortName)
        default_colors.append(team.TeamColor.Default)
        official_colors.append(team.TeamColor.Official)

        x_ranges.append((j + 0.5, 1))

    # draw color rectangles as horizontal bar graph
    ax.broken_barh(x_ranges, (0.5, 0.9), facecolors=official_colors)
    ax.broken_barh(x_ranges, (1.5, 0.9), facecolors=default_colors)

    # configure y axis and label
    ax.set_ylim((0.5, 2.5))
    ax.set_yticks([1, 2])
    ax.set_yticklabels(['official', 'default'])

    # configure x axis and label
    ax.set_xlim((0.5, len(x_ranges) + 0.5))
    ax.set_xticks(range(1, len(x_labels) + 1))
    ax.set_xticklabels(x_labels)

    # disable frame around axis
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    # disable tick markers everywhere, label x axis at the top
    ax.tick_params(top=False, labeltop=True, bottom=False, labelbottom=False,
                   left=False, labelleft=True, right=False, labelright=False)

    # set tick label text color (grey, so it works on light and dark theme and
    # isn't too distracting next to the colors)
    ax.tick_params(colors='#787878')

    # set background color within axes
    # (transparent, fallback white if transparency not supported)
    ax.set_facecolor('#ffffff00')

    # set axes title (grey, so it works on light and dark theme and
    # isn't too distracting next to the colors)
    ax.set_title(year, color='#787878')

# set background color for figure/margins around axes
# (transparent, fallback white if transparency not supported)
fig.patch.set_facecolor('#ffffff00')

# adjust margins between and around axes
plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.5)

plt.show()
