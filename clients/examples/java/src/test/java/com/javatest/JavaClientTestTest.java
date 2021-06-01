package com.javatest;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class JavaClientTestTest {

  @Test
  void testSendRequestAndGetHar() {
    var har = new JavaClientTest().sendRequestAndGetHar("https://google.com");

    assertNotNull(har, "Expected HAR to be not null");
    assertNotNull(har.getLog(), "Expected HAR Log to be not null");
    assertTrue(har.getLog().getEntries().size() > 0, "Expected to get some HAR entries, found 0");
    assertTrue(
        har.getLog().getEntries()
            .stream()
            .anyMatch(e -> e.getRequest().getUrl().toString().contains("google")),
        "Expected to find HAR Entry with url containing 'google'");
  }
}
