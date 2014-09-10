/**
 * Simple class to expose nanoTime() to JavaScript.
 *
 * Compile using
 *   javac -g:none -target 1.5 nano.java
 *   jar cfM nano.jar nano.class
 *   java -jar proguard.jar @options.txt
 *
 * ProGuard (http://proguard.sourceforge.net)
 * options.txt
 *   -injars      nano.jar
 *   -outjars     nano_s.jar
 *   -libraryjars <java.home>/jre/lib/rt.jar
 *   -keep public class nano {
 *     public long nanoTime();
 *   }
 */
import java.applet.Applet;
public class nano extends Applet {
  public long nanoTime() {
    return System.nanoTime();
  }
}
