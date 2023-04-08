# Spring Boot back end for Geo Tourist app

## References

### How to map '/' to index.html:

```java
@Override
public void addViewControllers(ViewControllerRegistry registry) {
    registry.addViewController("/").setViewName("forward:/index.html");
}
```
Ref. https://stackoverflow.com/questions/27381781/java-spring-boot-how-to-map-my-app-root-to-index-html

### How to serve up Web content in general:

https://spring.io/guides/gs/serving-web-content/

### How to package up the entire Web app: HTML, CSS, Javacript, image?

Anywhere beneath src/main/resources/static is an appropriate place for static
content such as CSS, JavaScript, and images. The static directory is served
from /. For example, src/main/resources/static/signin.css will be served from
/signin.css whereas src/main/resources/static/css/signin.css will be served
from /css/signin.css.

The src/main/resources/templates folder is intended for view templates that
will be turned into HTML by a templating engine such as Thymeleaf, Freemarker,
or Velocity, etc. You shouldn't place static content in this directory.

Also make sure you haven't used @EnableWebMvc in your application as that will
disable Spring Boot's auto-configuration of Spring MVC.

Ref. https://stackoverflow.com/questions/27170772/where-to-put-static-files-such-as-css-in-a-spring-boot-project

