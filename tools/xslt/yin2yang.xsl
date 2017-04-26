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

<stylesheet xmlns="http://www.w3.org/1999/XSL/Transform"
		xmlns:yin="urn:ietf:params:xml:ns:yang:yin:1"
		xmlns:html="http://www.w3.org/1999/xhtml"
		version="1.0">
  <output method="text"/>
  <strip-space elements="*"/>

  <!-- The 'date' parameter, if set, overrides the value of the
       first 'revision' statement. -->
  <param name="date"/>
  <!-- Amount of indentation added for each YANG hierarchy level. -->
  <param name="indent-step" select="2"/>
  <!-- Maximum line length -->
  <param name="line-length" select="70"/>
  <!-- Marks for unordered list items at different levels of
       embedding -->
  <param name="list-bullets" select="'-*o+'"/>

  <variable name="unit-indent">
    <call-template name="repeat-string">
      <with-param name="count" select="$indent-step"/>
      <with-param name="string" select="' '"/>
    </call-template>
  </variable>

  <template name="repeat-string">
    <param name="count"/>
    <param name="string"/>
    <choose>
      <when test="not($count) or not($string)"/>
      <when test="$count = 1">
	<value-of select="$string"/>
      </when>
      <otherwise>
	<if test="$count mod 2">
	  <value-of select="$string"/>
	</if>
	<call-template name="repeat-string">
	  <with-param name="count" select="floor($count div 2)"/>
	  <with-param name="string" select="concat($string,$string)"/>
	</call-template>
      </otherwise>
    </choose>
  </template>

  <template name="indent">
    <param name="level" select="count(ancestor::*)"/>
    <call-template name="repeat-string">
      <with-param name="count" select="$level"/>
      <with-param name="string" select="$unit-indent"/>
    </call-template>
  </template>

  <template name="fill-text">
    <param name="text"/>
    <param name="length"/>
    <param name="remains" select="$length"/>
    <param name="prefix"/>
    <param name="wdelim" select="' '"/>
    <param name="break" select="'&#xA;'"/>
    <param name="at-start" select="false()"/>
    <if test="string-length($text) &gt; 0">
      <variable name="next-word">
	<choose>
	  <when test="contains($text, $wdelim)">
	    <value-of select="substring-before($text, $wdelim)"/>
	  </when>
	  <otherwise>
	    <value-of select="$text"/>
	  </otherwise>
	</choose>
      </variable>
      <variable name="rest">
	<choose>
	  <when test="contains($text, $wdelim)">
	    <value-of select="substring-after($text, $wdelim)"/>
	  </when>
	  <otherwise>
	    <text></text>
	  </otherwise>
	</choose>
      </variable>
      <variable
	  name="left"
	  select="$remains - string-length(concat($wdelim,$next-word))"/>
      <choose>
	<when test="$at-start">
	  <value-of select="$next-word"/>
	  <call-template name="fill-text">
	    <with-param name="text" select="$rest"/>
	    <with-param name="length" select="$length"/>
	    <with-param name="remains" select="$left + 1"/>
	    <with-param name="prefix" select="$prefix"/>
	    <with-param name="wdelim" select="$wdelim"/>
	    <with-param name="break" select="$break"/>
	  </call-template>
	</when>
	<when test="$left &lt; string-length($break)">
	  <value-of select="concat($break,$prefix)"/>
	  <call-template name="fill-text">
	    <with-param name="text" select="$text"/>
	    <with-param name="length" select="$length"/>
	    <with-param name="remains" select="$length"/>
	    <with-param name="prefix" select="$prefix"/>
	    <with-param name="wdelim" select="$wdelim"/>
	    <with-param name="break" select="$break"/>
	    <with-param name="at-start" select="true()"/>
	  </call-template>
	</when>
	<otherwise>
	  <value-of select="concat($wdelim,$next-word)"/>
	  <call-template name="fill-text">
	    <with-param name="text" select="$rest"/>
	    <with-param name="length" select="$length"/>
	    <with-param name="remains" select="$left"/>
	    <with-param name="prefix" select="$prefix"/>
	    <with-param name="wdelim" select="$wdelim"/>
	    <with-param name="break" select="$break"/>
	  </call-template>
	</otherwise>
      </choose>
    </if>
  </template>

  <template name="semi-or-sub">
    <choose>
      <when test="*">
	<text> {&#xA;</text>
	<apply-templates select="*|comment()"/>
	<call-template name="indent"/>
	<text>}&#xA;</text>
      </when>
      <otherwise>
	<text>;&#xA;</text>
      </otherwise>
    </choose>
  </template>

  <template name="keyword">
    <if test="count(ancestor::*)=1">
      <text>&#xA;</text>
    </if>
    <call-template name="indent"/>
    <value-of select="local-name(.)"/>
  </template>

  <template name="statement">
    <param name="arg"/>
    <call-template name="keyword"/>
    <value-of select="concat(' ', $arg)"/>
    <call-template name="semi-or-sub"/>
  </template>

  <template name="statement-dq">    <!-- double-quoted arg -->
    <param name="arg"/>
    <call-template name="statement">
      <with-param name="arg">
	<text>"</text>
	<call-template name="escape-text">
	  <with-param name="text" select="$arg"/>
	</call-template>
	<text>"</text>
      </with-param>
    </call-template>
  </template>

  <template name="escape-text">
    <param name="text"/>
    <if test="string-length($text) &gt; 0">
      <call-template name="escape-char">
	<with-param name="char" select="substring($text,1,1)"/>
      </call-template>
      <call-template name="escape-text">
	<with-param name="text" select="substring($text,2)"/>
      </call-template>
    </if>
  </template>

  <template name="escape-char">
    <param name="char"/>
    <variable name="simple-escapes">"\</variable>
    <choose>
      <when test="contains($simple-escapes, $char)">
	<value-of select="concat('\', $char)"/>
      </when>
      <when test="$char='&#9;'">\t</when>
      <when test="$char='&#10;'">\n</when>
      <otherwise>
	<value-of select="$char"/>
      </otherwise>
    </choose>
  </template>

  <template name="chop-arg">
    <param name="token-delim" select="'/'"/>
    <variable name="qchar">"</variable>
    <variable name="cind">
      <call-template name="indent">
	<with-param name="level" select="count(ancestor::*)-1"/>
      </call-template>
    </variable>
    <variable name="txt">
      <call-template name="escape-text">
	<with-param name="text" select="normalize-space(.)"/>
      </call-template>
    </variable>
    <choose>
      <when
	  test="string-length(concat($cind,local-name(..),$txt))
		&lt; $line-length - 5">
	<value-of select="concat(' ',$qchar,$txt)"/>
      </when>
      <when test="string-length(concat($cind,$unit-indent,$txt))
		      &lt; $line-length - 4">
	<text>&#xA;</text>
	<call-template name="indent"/>
	<value-of select="concat($qchar,$txt)"/>
      </when>
      <otherwise>
	<value-of select="concat(' ',$qchar)"/>
	<call-template name="fill-text">
	  <with-param name="text" select="$txt"/>
	  <with-param
	      name="length"
	      select="$line-length - 2 -
		      string-length(concat($cind, local-name(..)))"/>
	  <with-param name="prefix">
	    <value-of select="$cind"/>
	    <call-template name="repeat-string">
	      <with-param
		  name="count"
		  select="string-length(local-name(..)) - 1"/>
	      <with-param name="string" select="' '"/>
	    </call-template>
	    <value-of select="concat('+ ',$qchar)"/>
	  </with-param>
	  <with-param name="wdelim" select="$token-delim"/>
	  <with-param name="break"
			  select="concat($token-delim,$qchar,'&#xA;')"/>
	  <with-param name="at-start" select="true()"/>
	</call-template>
      </otherwise>
    </choose>
    <value-of select="$qchar"/>
  </template>

  <!-- Root element -->

  <template match="/">
    <apply-templates select="yin:module|yin:submodule|comment()"/>
  </template>

  <template
      match="yin:action|yin:anydata|yin:anyxml|yin:argument|yin:base
	     |yin:bit|yin:case|yin:choice|yin:container|yin:enum
	     |yin:extension|yin:feature|yin:grouping|yin:identity
	     |yin:leaf|yin:leaf-list|yin:list
	     |yin:module|yin:notification|yin:rpc|yin:submodule
	     |yin:type|yin:typedef|yin:uses">
    <call-template name="statement">
      <with-param name="arg" select="@name"/>
    </call-template>
  </template>

  <template match="yin:if-feature|yin:units">
    <call-template name="statement-dq">
      <with-param name="arg" select="@name"/>
    </call-template>
  </template>

  <template match="yin:augment|yin:deviation|yin:refine">
    <call-template name="keyword"/>
    <apply-templates select="@target-node"/>
    <call-template name="semi-or-sub"/>
  </template>

  <template match="yin:belongs-to|yin:import|yin:include">
    <call-template name="statement">
      <with-param name="arg" select="@module"/>
    </call-template>
  </template>

  <template
      match="yin:config|yin:default|yin:deviate|yin:error-app-tag
	     |yin:fraction-digits|yin:key|yin:length|yin:mandatory
	     |yin:max-elements|yin:min-elements|yin:ordered-by
	     |yin:pattern|yin:position|yin:prefix
	     |yin:presence|yin:range|yin:require-instance
	     |yin:status|yin:value|yin:yang-version|yin:yin-element">
    <call-template name="statement-dq">
      <with-param name="arg" select="@value"/>
    </call-template>
  </template>

  <template match="yin:path|yin:pattern">
    <call-template name="keyword"/>
    <apply-templates select="@value"/>
    <call-template name="semi-or-sub"/>
  </template>

  <template match="@target-node|yin:path/@value">
    <call-template name="chop-arg"/>
  </template>

  <template match="yin:pattern/@value">
    <call-template name="chop-arg">
      <with-param name="token-delim">|</with-param>
    </call-template>
  </template>

  <template match="yin:error-message">
    <call-template name="keyword"/>
    <apply-templates select="yin:value"/>
  </template>

  <template match="yin:error-message/yin:value">
    <call-template name="chop-arg">
      <with-param name="token-delim" select="' '"/>
    </call-template>
    <text>;&#xA;</text>
  </template>

  <template match="yin:contact|yin:description
		       |yin:organization|yin:reference">
    <call-template name="keyword"/>
    <apply-templates select="yin:text"/>
  </template>

  <template match="yin:input|yin:output">
    <call-template name="keyword"/>
    <call-template name="semi-or-sub"/>
  </template>

  <template match="yin:must|yin:when">
    <call-template name="keyword"/>
    <apply-templates select="@condition"/>
    <call-template name="semi-or-sub"/>
  </template>

  <template match="@condition">
    <call-template name="chop-arg">
      <with-param name="token-delim">
	<choose>
	  <when test="contains(substring(.,0,$line-length),' ')">
	    <text> </text>
	  </when>
	  <otherwise>/</otherwise>
	</choose>
      </with-param>
    </call-template>
  </template>

  <template match="yin:namespace">
    <call-template name="statement-dq">
      <with-param name="arg" select="@uri"/>
    </call-template>
  </template>

  <template match="yin:revision">
    <call-template name="statement">
      <with-param name="arg">
	<choose>
	  <when test="$date and not(preceding-sibling::yin:revision)">
	    <value-of select="$date"/>
	  </when>
	  <otherwise>
	    <value-of select="@date"/>
	  </otherwise>
	</choose>
      </with-param>
    </call-template>
  </template>

  <template match="yin:revision-date">
    <call-template name="statement">
      <with-param name="arg" select="@date"/>
    </call-template>
  </template>

  <template match="yin:unique">
    <call-template name="statement-dq">
      <with-param name="arg" select="@tag"/>
    </call-template>
  </template>

  <template match="yin:text">
    <variable name="qchar">"</variable>
    <text>&#xA;</text>
    <variable name="prf">
      <call-template name="indent"/>
    </variable>
    <value-of select="concat($prf,$qchar)"/>
    <choose>
      <when test="html:*">
	<apply-templates select="html:p|html:ul|html:ol">
	  <with-param name="prefix" select="concat($prf,' ')"/>
	</apply-templates>
      </when>
      <otherwise>
	<call-template name="fill-text">
	  <with-param name="text">
	    <call-template name="escape-text">
	      <with-param
		  name="text"
		  select="normalize-space(.)"/>
	    </call-template>
	    <value-of select="concat($qchar,';&#xA;')"/>
	  </with-param>
	  <with-param
	      name="length"
	      select="$line-length - string-length($prf) - 1"/>
	  <with-param name="prefix" select="concat($prf,' ')"/>
	  <with-param name="at-start" select="true()"/>
	</call-template>
      </otherwise>
    </choose>
  </template>

  <template match="html:ul">
    <param name="prefix"/>
    <if test="position()>1">
      <value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </if>
    <apply-templates select="html:li">
      <with-param name="prefix" select="$prefix"/>
      <with-param name="last" select="position()=last()"/>
    </apply-templates>
  </template>

  <template match="html:ol">
    <param name="prefix"/>
    <if test="position()>1">
      <value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </if>
    <apply-templates select="html:li" mode="numbered">
      <with-param name="prefix" select="$prefix"/>
      <with-param name="last" select="position()=last()"/>
    </apply-templates>
  </template>

  <template match="html:p">
    <param name="prefix"/>
    <if test="position()>1">
      <value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </if>
    <apply-templates select="text()|html:br" mode="fill">
      <with-param name="prefix" select="$prefix"/>
      <with-param name="last" select="position()=last()"/>
    </apply-templates>
  </template>

  <template match="text()" mode="fill">
    <param name="prefix"/>
    <param name="last"/>
    <call-template name="fill-text">
      <with-param name="text">
	<call-template name="escape-text">
	  <with-param name="text" select="normalize-space(.)"/>
	</call-template>
	<if test="$last and position()=last()">";&#xA;</if>
      </with-param>
      <with-param
	  name="length"
	  select="$line-length - string-length($prefix)"/>
      <with-param name="prefix" select="$prefix"/>
      <with-param name="at-start" select="true()"/>
    </call-template>
  </template>

  <template match="html:br" mode="fill">
    <param name="prefix"/>
    <param name="last"/>
    <value-of select="concat('&#xA;',$prefix)"/>
    <if test="$last and position()=last()">";&#xA;</if>
  </template>

  <template match="html:li">
    <param name="prefix"/>
    <param name="last"/>
    <if test="position()>1">
      <value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </if>
    <value-of
	select="concat(substring($list-bullets,
		count(ancestor::html:ul),1),' ')"/>
    <call-template name="fill-text">
      <with-param name="text">
	<call-template name="escape-text">
	  <with-param name="text" select="normalize-space(.)"/>
	</call-template>
	<if test="$last and position()=last()">";&#xA;</if>
      </with-param>
      <with-param
	  name="length"
	  select="$line-length - string-length($prefix) - 2"/>
      <with-param name="prefix" select="concat($prefix,'  ')"/>
      <with-param name="at-start" select="true()"/>
    </call-template>
  </template>

  <template match="html:li" mode="numbered">
    <param name="prefix"/>
    <param name="last"/>
    <if test="position()>1">
      <value-of select="concat('&#xA;&#xA;',$prefix)"/>
    </if>
    <value-of
	select="concat(count(preceding-sibling::html:li) + 1,'. ')"/>
    <call-template name="fill-text">
      <with-param name="text">
	<call-template name="escape-text">
	  <with-param name="text" select="normalize-space(.)"/>
	</call-template>
	<if test="$last and position()=last()">";&#xA;</if>
      </with-param>
      <with-param
	  name="length"
	  select="$line-length - string-length($prefix) - 3"/>
      <with-param name="prefix" select="concat($prefix,'   ')"/>
      <with-param name="at-start" select="true()"/>
    </call-template>
  </template>

  <template match="comment()">
    <if test="count(ancestor::yin:*)=1">
      <text>&#xA;</text>
    </if>
    <call-template name="indent"/>
    <text>/*</text>
    <value-of select="."/>
    <text>*/&#xA;</text>
  </template>

  <!-- Extension -->
  <template match="*">
    <if test="count(ancestor::*)=1">
      <text>&#xA;</text>
    </if>
    <call-template name="indent"/>
    <value-of select="name(.)"/>
    <if test="@*">
      <text> "</text>
      <call-template name="escape-text">
	<with-param name="text" select="@*"/>
      </call-template>
      <text>"</text>
    </if>
    <call-template name="semi-or-sub"/>
  </template>

</stylesheet>
