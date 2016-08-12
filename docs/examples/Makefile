# This Makefile is designed to be run from a subdirectory of examples/docs
yams = $(patsubst %.yin,%.yang,$(wildcard *.yin))
EXAMPLE_BASE = example
EXAMPLE_TARGET = data
PYANG_OPTS =
IETF_DIR = ../../../examples/ietf
baty = $(EXAMPLE_BASE)-$(EXAMPLE_TARGET)
export YANG_MODPATH ?= .:$(IETF_DIR)
xsldir = ../../../tools/xslt
schemas = $(baty).rng $(baty).sch $(baty).dsrl
y2dopts = -t $(EXAMPLE_TARGET) -b $(EXAMPLE_BASE)
ylfile = yang-library-$(lastword $(subst /, ,$(abspath .))).json
rngparms = --stringparam target $(EXAMPLE_TARGET) \
	--stringparam basename $(EXAMPLE_BASE) \
	--stringparam schema-dir $(PYANG_RNG_LIBDIR) \
	$(PYANG_XSLT_DIR)/gen-relaxng.xsl
.PHONY: all clean commit json rnc skel yang

all: $(ylfile) $(baty).json

yang: $(yams)

json: $(baty).json

schema: $(schemas)

rnc: $(baty).rnc

hello.xml: $(yams)
	@echo '<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">' > $@
	@echo '<capabilities>' >> $@
	@echo '<capability>urn:ietf:params:netconf:base:1.1</capability>' >> $@
	@for m in $(yams); do \
	  capa=$$(pyang $(PYANG_OPTS) -f capability --capability-entity $$m); \
	  if [ "$$capa" != "" ]; then \
	    echo "<capability>$$capa</capability>" >> $@; \
	  fi \
	done
	@echo '</capabilities>' >> $@
	@echo '</hello>' >> $@

../yang-library.xsl: $(IETF_DIR)/ietf-yang-library@2016-06-21.yang
	@pyang $(PYANG_OPTS) -f jsonxsl -o $@ $<

$(ylfile): hello.xml ../yang-library.xsl
	@xsltproc $(xsldir)/hello2yanglib.xsl $< | \
	  xsltproc -o $@ ../yang-library.xsl -

%.yang: %.yin
	@xsltproc --xinclude $(xsldir)/canonicalize.xsl $< | \
	  xsltproc --output $@ $(yypars) $(xsldir)/yin2yang.xsl -

$(baty).dsdl: hello.xml
	@pyang $(PYANG_OPTS) -f dsdl -o $@ -L $<

$(baty).rng: $(baty).dsdl
	@xsltproc --output $@ $(rngparms) $<

$(EXAMPLE_BASE)-gdefs-config.rng: $(baty).dsdl
	@xsltproc --output $@ --stringparam gdefs-only 1 $(rngparms) $<

$(baty).rnc: $(baty).rng $(EXAMPLE_BASE)-gdefs-config.rng
	@trang -I rng -O rnc $< $@

$(baty).json: model.xsl $(baty).xml
	@xsltproc --output $@ $^

model.xsl: hello.xml
	@pyang $(PYANG_OPTS) -o $@ -f jsonxsl -L $<

model.tree: hello.xml
	@pyang $(PYANG_OPTS) -f tree -o $@ -L $<

skel: hello.xml
	@pyang $(PYANG_OPTS) -f sample-xml-skeleton \
	  --sample-xml-skeleton-defaults -L $< | \
	  xmllint -o $(baty).xml --format -

commit: $(yams) $(baty).json $(ylfile)
	@git add $^
	@git commit

clean:
	@rm -rf *.rng *.rnc *.dsdl *.xsl model.tree
