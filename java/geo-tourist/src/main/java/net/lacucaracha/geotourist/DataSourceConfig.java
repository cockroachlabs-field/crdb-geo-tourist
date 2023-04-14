package net.lacucaracha.geotourist;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import javax.sql.DataSource;

@Configuration
public class DataSourceConfig {

    Logger logger = LoggerFactory.getLogger(DataSourceConfig.class);

    @Autowired
    private Environment environment;

    @Bean
    public DataSource getDataSource() {
        DataSourceBuilder dataSourceBuilder = DataSourceBuilder.create();
        String jdbcUrl = environment.getProperty("spring.datasource.url");
        logger.info("JDBC URL: " + jdbcUrl);
        if (jdbcUrl.startsWith("jdbc:cockroachdb://")) {
            dataSourceBuilder.driverClassName("io.cockroachdb.jdbc.CockroachDriver");
        } else {
            dataSourceBuilder.driverClassName("org.postgresql.Driver");
        }
        dataSourceBuilder.url(jdbcUrl);
        return dataSourceBuilder.build();
    }

}
