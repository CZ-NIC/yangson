<?xml version="1.0" encoding="utf-8"?>
<!-- Program name: canonicalize.xsl

Copyright © 2013 by Ladislav Lhotka, CZ.NIC <lhotka@nic.cz>

This stylesheet rearranges a YIN module into canonical order [RFC 6020].

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
-->

<stylesheet xmlns="http://www.w3.org/1999/XSL/Transform"
		xmlns:xi="http://www.w3.org/2001/XInclude"
		xmlns:html="http://www.w3.org/1999/xhtml"
		xmlns:yin="urn:ietf:params:xml:ns:yang:yin:1"
		version="1.0">
  <output method="xml" encoding="utf-8"/>
  <strip-space elements="*"/>
  <param name="yin-ns">urn:ietf:params:xml:ns:yang:yin:1</param>

  <template name="preceding-comment">
    <if
	test="count((preceding-sibling::*|preceding-sibling::comment())
	      [last()]|preceding-sibling::comment()[1]) = 1">
      <apply-templates select="preceding-sibling::comment()[1]"/>
    </if>
  </template>
  <template match="html:*|xi:*|@*|comment()|text()">
    <copy-of select="."/>
  </template>
  <template name="data-def-stmt">
    <apply-templates
	select="yin:container|yin:leaf|yin:leaf-list|
		yin:list|yin:choice|yin:anyxml|yin:uses"/>
  </template>

  <template name="copy-extensions">
    <for-each select="*[namespace-uri() != $yin-ns]">
      <copy-of select="."/>
    </for-each>
  </template>

  <template match="yin:module">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:yang-version"/>
      <apply-templates select="yin:namespace"/>
      <apply-templates select="yin:prefix"/>
      <apply-templates select="yin:import"/>
      <apply-templates select="yin:include"/>
      <apply-templates select="yin:organization"/>
      <apply-templates select="yin:contact"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:revision"/>
      <apply-templates
	  select="yin:extension|yin:feature|yin:identity|yin:typedef|
		  yin:grouping|yin:container|yin:leaf|yin:leaf-list|
		  yin:list|yin:choice|yin:anyxml|yin:uses|yin:augment|
		  yin:rpc|yin:notification|yin:deviation"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:submodule">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:yang-version"/>
      <apply-templates select="yin:belongs-to"/>
      <apply-templates select="yin:import"/>
      <apply-templates select="yin:include"/>
      <apply-templates select="yin:organization"/>
      <apply-templates select="yin:contact"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:revision"/>
      <apply-templates
	  select="yin:extension|yin:feature|yin:identity|yin:typedef|
		  yin:grouping|yin:container|yin:leaf|yin:leaf-list|
		  yin:list|yin:choice|yin:anyxml|yin:uses|yin:augment|
		  yin:rpc|yin:notification|yin:deviation"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:feature">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:if-feature">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:identity">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:base"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:base">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:yang-version">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:import">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:prefix"/>
      <apply-templates select="yin:revision-date"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:revision-date">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:include">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:revision-date"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:namespace">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:prefix">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:belongs-to">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:prefix"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:organization">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:text"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:text">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:contact">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:text"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:description">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:text"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:reference">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:text"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:units">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:revision">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:extension">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:argument"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:argument">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:yin-element"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:yin-element">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:typedef">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:type"/>
      <apply-templates select="yin:units"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:type">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:fraction-digits"/>
      <apply-templates select="yin:range"/>
      <apply-templates select="yin:length"/>
      <apply-templates select="yin:pattern"/>
      <apply-templates select="yin:enum"/>
      <apply-templates select="yin:bit"/>
      <apply-templates select="yin:path"/>
      <apply-templates select="yin:base"/>
      <apply-templates select="yin:type"/>
      <apply-templates select="yin:require-instance"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:fraction-digits">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:range">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:error-message"/>
      <apply-templates select="yin:error-app-tag"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:length">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:error-message"/>
      <apply-templates select="yin:error-app-tag"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:pattern">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:error-message"/>
      <apply-templates select="yin:error-app-tag"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:default">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:enum">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:value"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:bit">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:position"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:position">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:path">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:require-instance">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:status">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:config">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:mandatory">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:presence">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:ordered-by">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:must">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:error-message"/>
      <apply-templates select="yin:error-app-tag"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:error-message">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:value"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:value">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:error-app-tag">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:min-elements">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:max-elements">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:value">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:grouping">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <apply-templates select="yin:action"/>
      <apply-templates select="yin:notification"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:container">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:presence"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <apply-templates select="yin:action"/>
      <apply-templates select="yin:notification"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:leaf">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:type"/>
      <apply-templates select="yin:units"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:mandatory"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:leaf-list">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:type"/>
      <apply-templates select="yin:units"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:min-elements"/>
      <apply-templates select="yin:max-elements"/>
      <apply-templates select="yin:ordered-by"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:list">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:key"/>
      <apply-templates select="yin:unique"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:min-elements"/>
      <apply-templates select="yin:max-elements"/>
      <apply-templates select="yin:ordered-by"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <apply-templates select="yin:action"/>
      <apply-templates select="yin:notification"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:key">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:unique">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:choice">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:mandatory"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:container"/>
      <apply-templates select="yin:leaf"/>
      <apply-templates select="yin:leaf-list"/>
      <apply-templates select="yin:list"/>
      <apply-templates select="yin:anyxml"/>
      <apply-templates select="yin:case"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:case">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="data-def-stmt"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:anyxml">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:mandatory"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:uses">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:refine"/>
      <apply-templates select="yin:augment"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:refine">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:presence"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:mandatory"/>
      <apply-templates select="yin:min-elements"/>
      <apply-templates select="yin:max-elements"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:augment">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:when"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="data-def-stmt"/>
      <apply-templates select="yin:case"/>
      <apply-templates select="yin:action"/>
      <apply-templates select="yin:notification"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:when">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:action|yin:rpc">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <apply-templates select="yin:input"/>
      <apply-templates select="yin:output"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:input">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:output">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:notification">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:if-feature"/>
      <apply-templates select="yin:status"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:typedef"/>
      <apply-templates select="yin:grouping"/>
      <call-template name="data-def-stmt"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:deviation">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:description"/>
      <apply-templates select="yin:reference"/>
      <apply-templates select="yin:deviate"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="yin:deviate">
    <call-template name="preceding-comment"/>
    <copy>
      <apply-templates select="html:*|xi:*|@*|text()"/>
      <apply-templates select="yin:type"/>
      <apply-templates select="yin:units"/>
      <apply-templates select="yin:must"/>
      <apply-templates select="yin:unique"/>
      <apply-templates select="yin:default"/>
      <apply-templates select="yin:config"/>
      <apply-templates select="yin:mandatory"/>
      <apply-templates select="yin:min-elements"/>
      <apply-templates select="yin:max-elements"/>
      <call-template name="copy-extensions"/>
    </copy>
  </template>
  <template match="/">
    <apply-templates select="yin:module"/>
    <apply-templates select="yin:submodule"/>
  </template>
</stylesheet>
