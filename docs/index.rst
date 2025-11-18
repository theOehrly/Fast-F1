######################
Introduction to FastF1
######################

.. toctree::
   :hidden:

   getting_started/index
   gen_modules/examples_gallery/index
   api_reference/index
   data_reference/index
   changelog/index
   contributing/index

FastF1 gives you access to F1 lap timing, car telemetry and position,
tyre data, weather data, the event schedule and session results.


.. raw:: html

    <style>
      .doc-tile-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 16px;
        margin: 30px 0;
      }
      .doc-tile {
        width: 165px;
        box-shadow: 0 4px 8px var(--pst-color-shadow, rgba(0, 0, 0, 0.1));
        border-radius: 5px;
        padding: 10px 16px 10px 16px;
        text-align: center;
        background-color: var(--pst-color-surface, var(--pst-color-background, white));
        transition: transform 0.3s, box-shadow 0.3s;
        text-decoration: none !important;
        color: inherit !important;
        display: block;
      }
      .doc-tile:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px var(--pst-color-shadow, rgba(0, 0, 0, 0.2));
      }
      .doc-tile h2 {
        margin-top: 0;
        font-size: 1.2rem;
        margin-bottom: 5px;
        color: var(--pst-color-text-base);
      }
      .doc-tile p {
        margin: 0;
        font-size: 0.9rem;
        color: var(--pst-color-text-muted, #666);
      }
      .doc-tile-icon {
        font-size: 3rem;
        margin-bottom: 15px;
        color: #e74c3c;
      }
    </style>

    <div class="doc-tile-container">

      <a href="getting_started/index.html" class="doc-tile">
        <div class="doc-tile-icon">📚</div>
        <h2>Getting<br>Started</h2>
        <p>Examples and tutorials to help you get started</p>
      </a>

      <!-- TODO:  add user guide
      <a href="user_guide/index.html" class="doc-tile">
        <div class="doc-tile-icon">📖</div>
        <h2>User Guide</h2>
        <p>Comprehensive guide to using FastF1 effectively</p>
      </a>
      -->

      <a href="api_reference/index.html" class="doc-tile">
        <div class="doc-tile-icon">🔍</div>
        <h2>API<br>Reference</h2>
        <p>Documentation of classes and functions</p>
      </a>

      <a href="data_reference/index.html" class="doc-tile">
        <div class="doc-tile-icon">📊</div>
        <h2>Data<br>Reference</h2>
        <p>Documentation of the available data</p>
      </a>

       <a href="gen_modules/examples_gallery/index.html" class="doc-tile">
         <div class="doc-tile-icon">🖼️</div>
         <h2>Example<br>Gallery</h2>
         <p>Examples showing FastF1's capabilities</p>
       </a>

      <a href="contributing/index.html" class="doc-tile">
        <div class="doc-tile-icon">⚙️</div>
        <h2>Development<br>&nbsp</h2>
        <p>How to contribute and help improve FastF1</p>
      </a>

    </div>



========
Features
========

- Access to F1 timing data, telemetry, sessions results and more
- Full support for the Ergast compatible `jolpica-f1 <https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md>`_ API to access current and
  historical F1 data
- All data is provided in the form of extended Pandas DataFrames to make
  working with the data easy while having powerful tools available
- Adds custom functions to the Pandas objects specifically to make working
  with F1 data quick and simple
- Integration with Matplotlib to facilitate data visualization
- Implements caching for all API requests to speed up your scripts


..
    To get a quick overview over how to use FastF1, check out
    :doc:`examples/index` or the :doc:`gen_modules/examples_gallery/index`.

    Note that FastF1 handles big chunks of data (~50-100mb per session). To improve
    performance, data is per default cached locally. The default placement
    of the cache is operating system specific. A custom location can be set if
    desired. For more information see :class:`~fastf1.req.Cache`.


=================
Third-party Tools
=================

These packages are not directly related to the FastF1 project. Questions and
suggestions regarding these packages need to be directed at their respective
maintainers.


SDKs
----

- **f1dataR**: R package that wraps FastF1 (https://cran.r-project.org/package=f1dataR)


Websites
--------

- **GP Tempo**: Web App for exploring F1 Telemetry Data (https://www.gp-tempo.com/)
- **Armchair Strategist**: Strategy dashboard for all F1 races since 2018 (https://armchair-strategist.dev/)


========================================================
Questions, Contacting the Maintainer and Code of Conduct
========================================================

For questions that may be of interest to the whole community, please use the
Github `Discussions <https://github.com/theOehrly/Fast-F1/discussions>`_
section to ask for help. This includes general support questions.

In case of questions that you need to discuss privately, feel free to contact
me via email at oehrly@mailbox.org. Any requests to this address will be
treated with confidentiality, if desired. **Do not use this email address for
general support requests! Such requests will likely be ignored.**

FastF1 has a `Code of Conduct <https://github.com/theOehrly/Fast-F1/blob/master/CODE_OF_CONDUCT.md>`_.
Complaints about a perceived breach of this code of conduct should be sent to
oehrly@mailbox.org, in almost all cases. Please refer to the Code of Conduct,
available through the main page of the GitHub repository (or click
`here <https://github.com/theOehrly/Fast-F1/blob/master/CODE_OF_CONDUCT.md>`_),
for information on how breaches are reported, how the
Code of Conduct is enforced and what values FastF1 encourages.


======
Notice
======

FastF1 and this website are unofficial and are not associated in any way with
the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD
CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One
Licensing B.V.

