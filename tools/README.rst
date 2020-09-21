This directory previously contained RELAX NG schemas and XSLT stylesheets intended for validating and transforming YANG modules in the XML syntax called `YIN <https://tools.ietf.org/html/rfc7950#section-13>`_:

* ``yin.rng`` – RELAX NG schema for YIN

* ``yin-html.rng`` – HTML-like extensions to YIN

* ``canonicalize.xsl`` – reorder YANG statements into the `canonical order <https://tools.ietf.org/html/rfc7950#section-14>`_

* ``yin2yang.xsl`` – convert YIN syntax to the standard compact syntax of YANG

These tools are now maintained in a separate project `yin-tools <https://github.com/llhotka/yin-tools>`_.
