===============
Video Map Tools
===============


.. image:: https://img.shields.io/pypi/v/videomap.svg
        :target: https://pypi.python.org/pypi/videomap

.. image:: https://img.shields.io/travis/openearth/videomap.svg
        :target: https://travis-ci.org/openearth/videomap

.. image:: https://readthedocs.org/projects/videomap/badge/?version=latest
        :target: https://videomap.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Tools to create,,  export and share video maps


* Free software: GNU General Public License v3
* Documentation: https://videomap.readthedocs.io.


Features
--------

* Convert a series of tiled maps to a tiled video

.. code:: sh

    videomap convert ~/data/frames

Where ~/data/frames contains frames in the structure

.. code:: sh

    ~/data/frames/{frame}/{z}/{x}/{y}.png

frame:  the frame number
z: zoom level
x: tile column
y: tile row

* Png's are converted to transparent webm contained vp8 with alpha channel.


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
