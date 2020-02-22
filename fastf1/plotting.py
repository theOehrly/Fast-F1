import matplotlib
from matplotlib import pyplot as plt
from matplotlib import cycler
import pandas as pd
import numpy as np
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

_TEAM_COLORS = {'MER': '#00d2be', 'FER': '#dc0000',
               'RBR': '#1e41ff', 'MCL': '#ff8700',
               'REN': '#fff500', 'RPT': '#f596c8',
               'ARR': '#9b0000', 'STR': '#469bff',
               'HAA': '#7e7e7e', 'WIL': '#469bff',
               'ALP': '#ffffff'}

TEAM_TRANSLATE = {'MER': 'Mercedes', 'FER': 'Ferrari',
                  'RBR': 'Red Bull', 'MCL': 'McLaren',
                  'REN': 'Renault', 'RPT': 'Racing Point',
                  'ARR': 'Alfa Romeo', 'STR': 'Toro Rosso',
                  'HAA': 'Haas F1 Team', 'WIL': 'Williams',
                  'ALP': 'Alpha Tauri'}

TEAM_COLORS = {}
for key in TEAM_TRANSLATE:
    TEAM_COLORS[TEAM_TRANSLATE[key]] = _TEAM_COLORS[key]

COLOR_PALETTE = ['#FF79C6', '#50FA7B', '#8BE9FD', '#BD93F9',
                 '#FFB86C', '#FF5555', '#F1FA8C']

def laptime_axis(ax, axis='yaxis'):
    def time_ticks(x, pos):
        if not np.isnan(x):
            pieces = f'{x - 60*int(x/60)}'.split('.')
            pieces[0] = pieces[0].zfill(2)
            x = f'{int(x/60)}:{".".join(pieces)}' 
        return x
    formatter = matplotlib.ticker.FuncFormatter(time_ticks)
    getattr(ax, axis).set_major_formatter(formatter)

def _bar_sorted(bar):
    def _bar_sorted_decorator(*args, **kwargs):
        if 'edgecolor' not in kwargs:
            kwargs['edgecolor'] = 'none'
        if 'sort' in kwargs and len(val := args[-1]):
            s = kwargs['sort']
            if s == 'increasing' or s == 1:
                s = False
            if s == 'decreasing' or s == -1:
                s = True
            _ids = [list(val).index(a) for a in sorted(val, reverse=s)]
            _args = [[args[-2][i] for i in _ids],
                     [args[-1][i] for i in _ids]]
            if len(args) > 2:
                _args.insert(0, args[0])
            args = _args
            for key in kwargs:
                if isinstance(kwargs[key], (pd.core.series.Series)):
                    kwargs[key] = kwargs[key].to_numpy()
                if isinstance(kwargs[key], (list, np.ndarray)):
                    kwargs[key] = [kwargs[key][i] for i in _ids]
            kwargs.pop('sort', None)
        return bar(*args, **kwargs)
    return _bar_sorted_decorator

plt.bar = _bar_sorted(plt.bar)
plt.barh = _bar_sorted(plt.barh)
matplotlib.axes.Axes.bar = _bar_sorted(matplotlib.axes.Axes.bar)
matplotlib.axes.Axes.barh = _bar_sorted(matplotlib.axes.Axes.barh)

def _nice_grid(ax):
    if isinstance(ax, np.ndarray):
        [_nice_grid(_ax) for _ax in ax]
    else:
        ax.minorticks_on()
        grid = getattr(ax, 'grid')
        grid(b=True, which='major', color='#4f4845', linestyle='-', linewidth=1)
        grid(b=True, which='minor', color='#3f3a38', linestyle='--', linewidth=0.5)

_subplots_placeholder = plt.subplots
def _subplots(*args, **kwargs):
    fig, ax = _subplots_placeholder(*args, **kwargs)
    _nice_grid(ax)
    return fig, ax
plt.subplots = _subplots

_savefig_placeholder = matplotlib.figure.Figure.savefig
def _save(*args, **kwargs):
    if 'facecolor' not in kwargs:
        kwargs['facecolor'] = args[0].get_facecolor()
    if 'edgecolors' not in kwargs:
        kwargs['edgecolor'] = 'none'
    return _savefig_placeholder(*args, **kwargs)
matplotlib.figure.Figure.savefig = _save


plt.rcParams['figure.facecolor'] = '#292625'
plt.rcParams['axes.edgecolor'] = '#2d2928'
plt.rcParams['xtick.color'] = '#f1f2f3' 
plt.rcParams['ytick.color'] = '#f1f2f3' 
plt.rcParams['axes.labelcolor'] = '#F1f2f3'
plt.rcParams['axes.facecolor'] = '#1e1c1b'
#plt.rcParams['axes.facecolor'] = '#292625'
plt.rcParams['axes.titlesize'] = 'x-large'
plt.rcParams['font.family'] = 'Gravity'
plt.rcParams['font.weight'] = 'medium'
plt.rcParams['text.color'] = '#F1F1F3'
plt.rcParams['axes.titlesize'] = '19'
plt.rcParams['axes.titlepad'] = '12'
plt.rcParams['axes.titleweight'] = 'light'
plt.rcParams['axes.prop_cycle'] = cycler('color', COLOR_PALETTE)
plt.rcParams['legend.fancybox'] = False
plt.rcParams['legend.facecolor'] = (0.1, 0.1, 0.1, 0.7)
plt.rcParams['legend.edgecolor'] = (0.1, 0.1, 0.1, 0.9)
plt.rcParams['savefig.transparent'] = False
plt.rcParams['axes.axisbelow'] = True
