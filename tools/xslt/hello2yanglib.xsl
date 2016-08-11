<?xml version="1.0" encoding="utf-8"?>
<!-- Program name: hello2yanglib.xsl

Copyright © 2016 by Ladislav Lhotka, CZ.NIC <lhotka@nic.cz>

This stylesheet transforms a NETCONF hello message to YANG library.

Limitations:
* submodules are not handled (because they don't appear in hello)
* deviations are ignored (TODO)
-->

<stylesheet xmlns="http://www.w3.org/1999/XSL/Transform"
		xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
		xmlns:yl="urn:ietf:params:xml:ns:yang:ietf-yang-library"
		version="1.0">
  <output method="xml" encoding="utf-8"/>
  <strip-space elements="*"/>

  <template name="uri-param">
    <param name="name-value"/>
    <variable name="name" select="substring-before($name-value, '=')"/>
    <variable name="value" select="substring-after($name-value, '=')"/>
    <choose>
      <when test="$name = 'module'">
	<element name="yl:name">
	  <value-of select="$value"/>
	</element>
      </when>
      <when test="$name = 'revision'">
	<element name="yl:revision">
	  <value-of select="$value"/>
	</element>
      </when>
      <when test="$name = 'features'">
	<call-template name="feature-list">
	  <with-param name="text" select="$value"/>
	</call-template> 
      </when>
    </choose>
  </template>

  <template name="uri-parameters">
    <param name="text"/>
    <choose>
      <when test="contains($text, '&amp;')">
	<call-template name="uri-param">
	  <with-param name="name-value"
		      select="substring-before($text, '&amp;')"/>
	</call-template>
	<call-template name="uri-parameters">
	  <with-param name="text" select="substring-after($text, '&amp;')"/>
	</call-template>
      </when>
      <otherwise>
	<call-template name="uri-param">
	  <with-param name="name-value" select="$text"/>
	</call-template>
      </otherwise>
    </choose>
  </template>
  
  <template name="feature-list">
    <param name="text"/>
    <choose>
      <when test="not($text)"/>
      <when test="contains($text, ',')">
	<element name="yl:feature">
	  <value-of select="substring-before($text, ',')"/>
	</element>
	<call-template name="feature-list">
	  <with-param name="text" select="substring-after($text, ',')"/>
	</call-template>
      </when>
      <otherwise>
	<element name="yl:feature">
	  <value-of select="$text"/>
	</element>
      </otherwise>
    </choose>
  </template>
  
  <template match="nc:hello">
    <apply-templates select="nc:capabilities"/>
  </template>

  <template match="nc:capabilities">
    <element name="nc:data">
      <element name="yl:modules-state">
	<element name="yl:module-set-id">XXXX</element>
	<apply-templates select="nc:capability[contains(., 'module=')]"/>
      </element>
    </element>
  </template>

  <template match="nc:capability">
    <element name="yl:module">
      <variable name="pars" select="substring-after(., '?')"/>
      <call-template name="uri-parameters">
	<with-param name="text" select="$pars"/>
      </call-template>
      <element name="yl:namespace">
	<value-of select="substring-before(., '?')"/>
      </element>
      <if test="not(contains($pars, 'revision='))">
	<element name="yl:revision"/>
      </if>
      <element name="yl:conformance-type">implement</element>
    </element>
  </template>

</stylesheet>
