package com.javatest;

import com.browserup.proxy.api.BrowserUpProxyApi;
import com.browserup.proxy_client.ApiClient;
import com.browserup.proxy_client.ApiException;
import com.browserup.proxy_client.Har;
import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

public class JavaClientTest {
  private static final Integer PROXY_PORT = 8080;

  public Har sendRequestAndGetHar(String url) {
    WebDriverManager.chromedriver().setup();

    var options = new ChromeOptions().addArguments(
        "--headless",
        "--disable-extensions",
        "--proxy-server=http://localhost:" + PROXY_PORT);

    var driver = new ChromeDriver(options);

    driver.get(url);

    Har harLog;
    try {
      harLog = new BrowserUpProxyApi().getHarLog();
    } catch (ApiException e) {
      throw new RuntimeException(e);
    } finally {
      driver.quit();
    }
    return harLog;
  }
}
