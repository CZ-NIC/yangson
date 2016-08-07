<?xml version="1.0"?>

<!-- Program name: yin2yang.xsl

Copyright © 2013 by Ladislav Lhotka, CZ.NIC <lhotka@nic.cz>

Translates YIN to YANG (see RFC 6020).

NOTES:

1. XML comments outside arguments are translated to YANG comments. 

2. This stylesheet supports the following non-standard YIN extension:

Arguments of 'contact', 'description', 'organization' and 'reference'
(wrapped in <text>) may contain the following HTML elements in the
"http://www.w3.org/1999/xhtml" namespace:

<html:p> - a paragraph of text
<html:ul> - unordered list
<html:ol> - ordered list

<html:p> elements may, apart from text, also contain empty
<html:br/> elements that cause an unconditional line break.

List elements must contain one or more <html:li> elements
representing list items with text and <html:br/> elements.

A <text> element may also have the xml:id attribute and contain the
XInclude element <xi:include>.

==

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

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:yin="urn:ietf:params:xml:ns:yang:yin:1"
		xmlns:html="http://www.w3.org/1999/xhtml"
		version="1.0">
  <xsl:output method="text"/>
  <xsl:strip-space elements="*"/>

  <!-- The 'date' parameter, if set, overrides the value of the
       'revision' statement. -->
  <xsl:param name="date"/>
  <!-- Amount of indentation added for each YANG hierarchy level. -->
  <xsl:param name="indent-step" select="2"/>
  <!-- Maximum line length -->
  <xsl:param name="line-length" select="70"/>
  <!-- Marks for unordered list items at different levels of
       embedding -->
  <xsl:param name="list-bullets" select="'-*o+'"/>

  <xsl:variable name="revision">
    <xsl:choose>
      <xsl:when test="$date">
	<xsl:value-of select="$date"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:value-of select="/yin:module/yin:revision/@date"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>

  <xsl:variable name="unit-indent">
    <xsl:call-template name="repeat-string">
      <xsl:with-param name="count" select="$indent-step"/>
      <xsl:with-param name="string" select="' '"/>
    </xsl:call-template>
  </xsl:variable>

  <xsl:template name="repeat-string">
    <xsl:param name="count"/>
    <xsl:param name="string"/>
    <xsl:choose>
      <xsl:when test="not($count) or not($string)"/>
      <xsl:when test="$count = 1">
	<xsl:value-of select="$string"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:if test="$count mod 2">
	  <xsl:value-of select="$string"/>
	</xsl:if>
	<xsl:call-template name="repeat-string">
	  <xsl:with-param name="count" select="floor($count div 2)"/>
	  <xsl:with-param name="string" select="concat($string,$string)"/>
	</xsl:call-template> 
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template name="indent">
    <xsl:param name="level" select="count(ancestor::*)"/>
    <xsl:call-template name="repeat-string">
      <xsl:with-param name="count" select="$level"/>
      <xsl:with-param name="string" select="$unit-indent"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template name="fill-text">
    <xsl:param name="text"/>
    <xsl:param name="length"/>
    <xsl:param name="remains" select="$length"/>
    <xsl:param name="prefix"/>
    <xsl:param name="wdelim" select="' '"/>
    <xsl:param name="break" select="'&#xA;'"/>
    <xsl:param name="at-start" select="false()"/>
    <xsl:if test="string-length($text) &gt; 0">
      <xsl:variable name="next-word">
	<xsl:choose>
	  <xsl:when test="contains($text, $wdelim)">
	    <xsl:value-of select="substring-before($text, $wdelim)"/>
	  </xsl:when>
	  <xsl:otherwise>
	    <xsl:value-of select="$text"/>
	  </xsl:otherwise>
	</xsl:choose>
      </xsl:variable>
      <xsl:variable name="rest">
	<xsl:choose>
	  <xsl:when test="contains($text, $wdelim)">
	    <xsl:value-of select="substring-after($text, $wdelim)"/>
	  </xsl:when>
	  <xsl:otherwise>
	    <xsl:text></xsl:text>
	  </xsl:otherwise>
	</xsl:choose>
      </xsl:variable>
      <xsl:variable
	  name="left"
	  select="$remains - string-length(concat($wdelim,$next-word))"/>
      <xsl:choose>
	<xsl:when test="$at-start">
	  <xsl:value-of select="$next-word"/>
	  <xsl:call-template name="fill-text">
	    <xsl:with-param name="text" select="$rest"/>
	    <xsl:with-param name="length" select="$length"/>
	    <xsl:with-param name="remains" select="$left + 1"/>
	    <xsl:with-param name="prefix" select="$prefix"/>
	    <xsl:with-param name="wdelim" select="$wdelim"/>
	    <xsl:with-param name="break" select="$break"/>
	  </xsl:call-template>
	</xsl:when>
	<xsl:when test="$left &lt; string-length($break)">
	  <xsl:value-of select="concat($break,$prefix)"/>
	  <xsl:call-template name="fill-text">
	    <xsl:with-param name="text" select="$text"/>
	    <xsl:with-param name="length" select="$length"/>
	    <xsl:with-param name="remains" select="$length"/>
	    <xsl:with-param name="prefix" select="$prefix"/>
	    <xsl:with-param name="wdelim" select="$wdelim"/>
	    <xsl:with-param name="break" select="$break"/>
	    <xsl:with-param name="at-start" select="true()"/>
	  </xsl:call-template>
	</xsl:when>
	<xsl:otherwise>
	  <xsl:value-of select="concat($wdelim,$next-word)"/>
	  <xsl:call-template name="fill-text">
	    <xsl:with-param name="text" select="$rest"/>
	    <xsl:with-param name="length" select="$length"/>
	    <xsl:with-param name="remains" select="$left"/>
	    <xsl:with-param name="prefix" select="$prefix"/>
	    <xsl:with-param name="wdelim" select="$wdelim"/>
	    <xsl:with-param name="break" select="$break"/>
	  </xsl:call-template>
	</xsl:otherwise>
      </xsl:choose>
    </xsl:if>
  </xsl:template>

  <xsl:template name="semi-or-sub">
    <xsl:choose>
      <xsl:when test="*">
	<xsl:text> {&#xA;</xsl:text>
	<xsl:apply-templates select="*|comment()"/>
	<xsl:call-template name="indent"/>
	<xsl:text>}&#xA;</xsl:text>
      </xsl:when>
      <xsl:otherwise>
	<xsl:text>;&#xA;</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template name="keyword">
    <xsl:if test="count(ancestor::*)=1">
      <xsl:text>&#xA;</xsl:text>
    </xsl:if>
    <xsl:call-template name="indent"/>
    <xsl:value-of select="local-name(.)"/>
  </xsl:template>

  <xsl:template name="statement">
    <xsl:param name="arg"/>
    <xsl:call-template name="keyword"/>
    <xsl:value-of select="concat(' ', $arg)"/>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

  <xsl:template name="statement-dq">    <!-- double-quoted arg -->
    <xsl:param name="arg"/>
    <xsl:call-template name="statement">
      <xsl:with-param name="arg">
	<xsl:text>"</xsl:text>
	<xsl:call-template name="escape-text">
	  <xsl:with-param name="text" select="$arg"/>
	</xsl:call-template>
	<xsl:text>"</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>

  <xsl:template name="escape-text">
    <xsl:param name="text"/>
    <xsl:if test="string-length($text) &gt; 0">
      <xsl:call-template name="escape-char">
	<xsl:with-param name="char" select="substring($text,1,1)"/>
      </xsl:call-template>
      <xsl:call-template name="escape-text">
	<xsl:with-param name="text" select="substring($text,2)"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template name="escape-char">
    <xsl:param name="char"/>
    <xsl:variable name="simple-escapes">"\</xsl:variable>
    <xsl:choose>
      <xsl:when test="contains($simple-escapes, $char)">
	<xsl:value-of select="concat('\', $char)"/>
      </xsl:when>
      <xsl:when test="$char='&#9;'">\t</xsl:when>
      <xsl:when test="$char='&#10;'">\n</xsl:when>
      <xsl:otherwise>
	<xsl:value-of select="$char"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template name="chop-arg">
    <xsl:param name="token-delim" select="'/'"/>
    <xsl:variable name="qchar">"</xsl:variable>
    <xsl:variable name="cind">
      <xsl:call-template name="indent">
	<xsl:with-param name="level" select="count(ancestor::*)-1"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="txt">
      <xsl:call-template name="escape-text">
	<xsl:with-param name="text" select="normalize-space(.)"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:choose>
      <xsl:when
	  test="string-length(concat($cind,local-name(..),$txt))
		&lt; $line-length - 5">
	<xsl:value-of select="concat(' ',$qchar,$txt)"/>
      </xsl:when>
      <xsl:when test="string-length(concat($cind,$unit-indent,$txt))
		      &lt; $line-length - 4">
	<xsl:text>&#xA;</xsl:text>
	<xsl:call-template name="indent"/>
	<xsl:value-of select="concat($qchar,$txt)"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:value-of select="concat(' ',$qchar)"/>
	<xsl:call-template name="fill-text">
	  <xsl:with-param name="text" select="$txt"/>
	  <xsl:with-param
	      name="length"
	      select="$line-length - 2 -
		      string-length(concat($cind, local-name(..)))"/>
	  <xsl:with-param name="prefix">
	    <xsl:value-of select="$cind"/>
	    <xsl:call-template name="repeat-string">
	      <xsl:with-param
		  name="count"
		  select="string-length(local-name(..)) - 1"/>
	      <xsl:with-param name="string" select="' '"/>
	    </xsl:call-template>
	    <xsl:value-of select="concat('+ ',$qchar)"/>
	  </xsl:with-param>
	  <xsl:with-param name="wdelim" select="$token-delim"/>
	  <xsl:with-param name="break"
			  select="concat($token-delim,$qchar,'&#xA;')"/>
	  <xsl:with-param name="at-start" select="true()"/>
	</xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:value-of select="$qchar"/>
  </xsl:template>

  <!-- Root element -->

  <xsl:template match="/">
    <xsl:apply-templates select="yin:module|yin:submodule|comment()"/>
  </xsl:template>

  <xsl:template
      match="yin:action|yin:anydata|yin:anyxml|yin:argument|yin:base
	     |yin:bit|yin:case|yin:choice|yin:container|yin:enum
	     |yin:extension|yin:feature|yin:grouping|yin:identity
	     |yin:if-feature|yin:leaf|yin:leaf-list|yin:list
	     |yin:module|yin:notification|yin:rpc|yin:submodule
	     |yin:type|yin:typedef|yin:uses">
    <xsl:call-template name="statement">
      <xsl:with-param name="arg" select="@name"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:units">
    <xsl:call-template name="statement-dq">
      <xsl:with-param name="arg" select="@name"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:augment|yin:deviation|yin:refine">
    <xsl:call-template name="keyword"/>
    <xsl:apply-templates select="@target-node"/>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

  <xsl:template match="yin:belongs-to|yin:import|yin:include">
    <xsl:call-template name="statement">
      <xsl:with-param name="arg" select="@module"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template
      match="yin:config|yin:default|yin:deviate|yin:error-app-tag
	     |yin:fraction-digits|yin:key|yin:length|yin:mandatory
	     |yin:max-elements|yin:min-elements|yin:ordered-by
	     |yin:pattern|yin:position|yin:prefix
	     |yin:presence|yin:range|yin:require-instance
	     |yin:status|yin:value|yin:yang-version|yin:yin-element">
    <xsl:call-template name="statement-dq">
      <xsl:with-param name="arg" select="@value"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:path|yin:pattern">
    <xsl:call-template name="keyword"/>
    <xsl:apply-templates select="@value"/>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

  <xsl:template match="@target-node|yin:path/@value">
    <xsl:call-template name="chop-arg"/>
  </xsl:template>

  <xsl:template match="yin:pattern/@value">
    <xsl:call-template name="chop-arg">
      <xsl:with-param name="token-delim">|</xsl:with-param>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:error-message">
    <xsl:call-template name="keyword"/>
    <xsl:apply-templates select="yin:value"/>
  </xsl:template>

  <xsl:template match="yin:error-message/yin:value">
    <xsl:call-template name="chop-arg">
      <xsl:with-param name="token-delim" select="' '"/>
    </xsl:call-template>
    <xsl:text>;&#xA;</xsl:text>
  </xsl:template>

  <xsl:template match="yin:contact|yin:description
		       |yin:organization|yin:reference">
    <xsl:call-template name="keyword"/>
    <xsl:apply-templates select="yin:text"/>
  </xsl:template>

  <xsl:template match="yin:input|yin:output">
    <xsl:call-template name="keyword"/>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

  <xsl:template match="yin:must|yin:when">
    <xsl:call-template name="keyword"/>
    <xsl:apply-templates select="@condition"/>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

  <xsl:template match="@condition">
    <xsl:call-template name="chop-arg">
      <xsl:with-param name="token-delim">
	<xsl:choose>
	  <xsl:when test="contains(substring(.,0,$line-length),' ')">
	    <xsl:text> </xsl:text>
	  </xsl:when>
	  <xsl:otherwise>/</xsl:otherwise>
	</xsl:choose>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:namespace">
    <xsl:call-template name="statement-dq">
      <xsl:with-param name="arg" select="@uri"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:revision">
    <xsl:call-template name="statement">
      <xsl:with-param name="arg" select="$revision"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:revision-date">
    <xsl:call-template name="statement">
      <xsl:with-param name="arg" select="@date"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:unique">
    <xsl:call-template name="statement-dq">
      <xsl:with-param name="arg" select="@tag"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="yin:text">
    <xsl:variable name="qchar">"</xsl:variable>
    <xsl:text>&#xA;</xsl:text>
    <xsl:variable name="prf">
      <xsl:call-template name="indent"/>
    </xsl:variable>
    <xsl:value-of select="concat($prf,$qchar)"/>
    <xsl:choose>
      <xsl:when test="html:*">
	<xsl:apply-templates select="html:p|html:ul|html:ol">
	  <xsl:with-param name="prefix" select="concat($prf,' ')"/>
	</xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
	<xsl:call-template name="fill-text">
	  <xsl:with-param name="text">
	    <xsl:call-template name="escape-text">
	      <xsl:with-param
		  name="text"
		  select="normalize-space(.)"/>
	    </xsl:call-template>
	    <xsl:value-of select="concat($qchar,';&#xA;')"/>
	  </xsl:with-param>
	  <xsl:with-param
	      name="length"
	      select="$line-length - string-length($prf) - 1"/>
	  <xsl:with-param name="prefix" select="concat($prf,' ')"/>
	  <xsl:with-param name="at-start" select="true()"/>
	</xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="html:ul">
    <xsl:param name="prefix"/>
    <xsl:if test="position()>1">
      <xsl:value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </xsl:if>
    <xsl:apply-templates select="html:li">
      <xsl:with-param name="prefix" select="$prefix"/>
      <xsl:with-param name="last" select="position()=last()"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="html:ol">
    <xsl:param name="prefix"/>
    <xsl:if test="position()>1">
      <xsl:value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </xsl:if>
    <xsl:apply-templates select="html:li" mode="numbered">
      <xsl:with-param name="prefix" select="$prefix"/>
      <xsl:with-param name="last" select="position()=last()"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="html:p">
    <xsl:param name="prefix"/>
    <xsl:if test="position()>1">
      <xsl:value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </xsl:if>
    <xsl:apply-templates select="text()|html:br" mode="fill">
      <xsl:with-param name="prefix" select="$prefix"/>
      <xsl:with-param name="last" select="position()=last()"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="text()" mode="fill">
    <xsl:param name="prefix"/>
    <xsl:param name="last"/>
    <xsl:call-template name="fill-text">
      <xsl:with-param name="text">
	<xsl:call-template name="escape-text">
	  <xsl:with-param name="text" select="normalize-space(.)"/>
	</xsl:call-template>
	<xsl:if test="$last and position()=last()">";&#xA;</xsl:if>
      </xsl:with-param>
      <xsl:with-param
	  name="length"
	  select="$line-length - string-length($prefix)"/>
      <xsl:with-param name="prefix" select="$prefix"/>
      <xsl:with-param name="at-start" select="true()"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="html:br" mode="fill">
    <xsl:param name="prefix"/>
    <xsl:param name="last"/>
    <xsl:value-of select="concat('&#xA;',$prefix)"/>
    <xsl:if test="$last and position()=last()">";&#xA;</xsl:if>
  </xsl:template>

  <xsl:template match="html:li">
    <xsl:param name="prefix"/>
    <xsl:param name="last"/>
    <xsl:if test="position()>1">
      <xsl:value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </xsl:if>
    <xsl:value-of
	select="concat(substring($list-bullets,
		count(ancestor::html:ul),1),' ')"/>
    <xsl:call-template name="fill-text">
      <xsl:with-param name="text">
	<xsl:call-template name="escape-text">
	  <xsl:with-param name="text" select="normalize-space(.)"/>
	</xsl:call-template>
	<xsl:if test="$last and position()=last()">";&#xA;</xsl:if>
      </xsl:with-param>
      <xsl:with-param
	  name="length"
	  select="$line-length - string-length($prefix) - 2"/>
      <xsl:with-param name="prefix" select="concat($prefix,'  ')"/>
      <xsl:with-param name="at-start" select="true()"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="html:li" mode="numbered">
    <xsl:param name="prefix"/>
    <xsl:param name="last"/>
    <xsl:if test="position()>1">
      <xsl:value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </xsl:if>
    <xsl:value-of
	select="concat(count(preceding-sibling::html:li) + 1,'. ')"/>
    <xsl:call-template name="fill-text">
      <xsl:with-param name="text">
	<xsl:call-template name="escape-text">
	  <xsl:with-param name="text" select="normalize-space(.)"/>
	</xsl:call-template>
	<xsl:if test="$last and position()=last()">";&#xA;</xsl:if>
      </xsl:with-param>
      <xsl:with-param
	  name="length"
	  select="$line-length - string-length($prefix) - 3"/>
      <xsl:with-param name="prefix" select="concat($prefix,'   ')"/>
      <xsl:with-param name="at-start" select="true()"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="comment()">
    <xsl:if test="count(ancestor::yin:*)=1">
      <xsl:text>&#xA;</xsl:text>
    </xsl:if>
    <xsl:call-template name="indent"/>
    <xsl:text>/*</xsl:text>
    <xsl:value-of select="."/>
    <xsl:text>*/&#xA;</xsl:text>
  </xsl:template>

  <!-- Extension -->
  <xsl:template match="*">
    <xsl:if test="count(ancestor::*)=1">
      <xsl:text>&#xA;</xsl:text>
    </xsl:if>
    <xsl:call-template name="indent"/>
    <xsl:value-of select="name(.)"/>
    <xsl:text> "</xsl:text>
    <xsl:call-template name="escape-text">
      <xsl:with-param name="text" select="@*"/>
    </xsl:call-template>
    <xsl:text>"</xsl:text>
    <xsl:call-template name="semi-or-sub"/>
  </xsl:template>

</xsl:stylesheet>
