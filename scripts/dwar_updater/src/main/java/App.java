import java.sql.*;
import java.util.Properties;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class App {

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    public static void main(String[] args) {
        System.out.println("=== DEEP CRITICAL MOLFILE DEBAGGING ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);

        IDCodeParser parser = new IDCodeParser();

        try (Connection conn = DriverManager.getConnection(DB_URL, props)) {

            // Включаем максимальный уровень логирования для текущей сессии,
            // чтобы поймать сообщения от RDKit (WARNING/NOTICE) прямо в Java
            try (Statement setStmt = conn.createStatement()) {
                setStmt.execute("SET client_min_messages = 'NOTICE';");
            }

            String selectQuery = "SELECT id, idcode, id_coords_2d FROM book_base WHERE id = 48673;";
            String cleanMolfile = "";

            try (PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
                 ResultSet rs = selectStmt.executeQuery()) {
                if (rs.next()) {
                    StereoMolecule mol = new StereoMolecule();
                    parser.parse(mol, rs.getString("idcode"), rs.getString("id_coords_2d"));

                    MolfileCreator creator = new MolfileCreator(mol);
                    String rawMolfile = creator.getMolfile();

                    // 1. Разбиваем на строки
                    String[] lines = rawMolfile.split("\\r?\\n");
                    java.util.List<String> cleanLines = new java.util.ArrayList<>();

                    for (String line : lines) {
                        StringBuilder sb = new StringBuilder();
                        for (int i = 0; i < line.length(); i++) {
                            char c = line.charAt(i);

                            // 160 — это десятичный код NBSP (\u00A0)
                            // 8203 — это Zero-Width Space, на всякий случай
                            if (c == 160 || Character.isWhitespace(c)) {
                                // Если это любой пробельный символ или жесткий NBSP — превращаем строго в ASCII-пробел (32)
                                sb.append(' ');
                            } else if (c == 8203) {
                                // Нулевой пробел просто дропаем
                                continue;
                            } else {
                                sb.append(c);
                            }
                        }
                        cleanLines.add(sb.toString());
                    }

                    // 2. Ищем строку с V2000
                    int countsLineIndex = -1;
                    for (int i = 0; i < cleanLines.size(); i++) {
                        if (cleanLines.get(i).contains("V2000")) {
                            countsLineIndex = i;
                            break;
                        }
                    }

                    StringBuilder validMolfile = new StringBuilder();

                    if (countsLineIndex != -1) {
                        // Жестко фиксируем структуру заголовка (первые 4 строки)
                        validMolfile.append("Actelion Java MolfileCreator 1.0\n"); // 1
                        validMolfile.append("\n");                                // 2
                        validMolfile.append("\n");                                // 3
                        validMolfile.append(cleanLines.get(countsLineIndex)).append("\n"); // 4 (Counts Line)

                        // Пишем все остальные строки
                        for (int i = countsLineIndex + 1; i < cleanLines.size(); i++) {
                            validMolfile.append(cleanLines.get(i)).append("\n");
                        }
                    } else {
                        for (String line : cleanLines) {
                            validMolfile.append(line).append("\n");
                        }
                    }

                    cleanMolfile = validMolfile.toString();
                }
            }

            // Добавим слушатель предупреждений JDBC
            conn.clearWarnings();

            // --- ПОЛНЫЙ ДЕБАГ ПОСТГРЕСА И RDKIT ---
            System.out.println("\n=== POSTGRESQL EXTENSION & FUNCTION DIAGNOSTICS ===");

            // 1. Проверяем, установлено ли расширение rdkit вообще
            String checkExtSql = "SELECT extname, extversion FROM pg_extension WHERE extname = 'rdkit';";
            try (Statement stmt = conn.createStatement(); ResultSet rs = stmt.executeQuery(checkExtSql)) {
                if (rs.next()) {
                    System.out.println("[DB INFO] Extension 'rdkit' IS INSTALLED. Version: " + rs.getString("extversion"));
                } else {
                    System.out.println("[DB ERROR] Extension 'rdkit' is NOT installed in this database!");
                    System.out.println("-> Действие: Выполни в консоли базы: CREATE EXTENSION rdkit;");
                }
            }

            // 2. Ищем, в какой схеме лежат функции RDKit и как они точно называются
            String findFuncSql =
                    "SELECT n.nspname as schema, p.proname as function " +
                            "FROM pg_proc p " +
                            "JOIN pg_namespace n ON p.pronamespace = n.oid " +
                            "WHERE p.proname LIKE '%mol%from%' OR p.proname LIKE '%ctab%';";

            boolean foundAnyFunction = false;
            String schemaPrefix = "";
            String correctFunctionName = "mol_from_ctab"; // дефолт

            try (Statement stmt = conn.createStatement(); ResultSet rs = stmt.executeQuery(findFuncSql)) {
                System.out.println("[DB INFO] Found matching RDKit functions in catalog:");
                while (rs.next()) {
                    foundAnyFunction = true;
                    String schema = rs.getString("schema");
                    String func = rs.getString("function");
                    System.out.println("   -> " + schema + "." + func);

                    if (func.equalsIgnoreCase("mol_from_ctab") || func.equalsIgnoreCase("mol_from_text")) {
                        schemaPrefix = schema + ".";
                        correctFunctionName = func;
                    }
                }
                if (!foundAnyFunction) {
                    System.out.println("[DB ERROR] No RDKit parsing functions found at all! Is the cartridge broken?");
                }
            }

            // 3. Проверяем текущий search_path базы
            try (Statement stmt = conn.createStatement(); ResultSet rs = stmt.executeQuery("SHOW search_path;")) {
                if (rs.next()) {
                    System.out.println("[DB INFO] Current search_path: " + rs.getString(1));
                }
            }

            // 4. Пробуем сделать тестовый парсинг с учетом найденной схемы
            // Если схема public, префикс будет "", если другая (например, rdkit) — будет "rdkit."
            String targetedSql = "SELECT " + schemaPrefix + correctFunctionName + "(?::text);";
            System.out.println("[DB INFO] Executing target query: " + targetedSql);
            // 4. Пробуем пробить сигнатуру типов для mol_from_ctab
            System.out.println("\n[DB INFO] Тестируем разные варианты приведения типов для mol_from_ctab:");

            // Вариант А: Через явный каст к cstring (очень часто у функций картриджей C-сигнатура)
            String sqlOptionA = "SELECT public.mol_from_ctab(?::cstring);";
            // Вариант Б: Добавляем дефолтные булевые аргументы (в некоторых версиях RDKit у неё сигнатура: mol_from_ctab(text, bool default true))
            String sqlOptionB = "SELECT public.mol_from_ctab(?::text, true);";
            // Вариант В: Через встроенную ленивую функцию парсинга текста (которая сама внутри вызывает нужный тип)
            String sqlOptionВ = "SELECT public.mol_from_text(?::text);";

            // Пробуем Вариант А
            try (PreparedStatement stmt = conn.prepareStatement(sqlOptionA)) {
                stmt.setString(1, cleanMolfile);
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("-> [УСПЕХ] Вариант А (?::cstring) СРАБОТАЛ!");
                    }
                }
            } catch (SQLException e) {
                System.out.println("-> [ОТКАЗ] Вариант А (?::cstring) мимо: " + e.getMessage().trim());

                // Пробуем Вариант Б
                try (PreparedStatement stmt = conn.prepareStatement(sqlOptionB)) {
                    stmt.setString(1, cleanMolfile);
                    try (ResultSet rs = stmt.executeQuery()) {
                        if (rs.next()) {
                            System.out.println("-> [УСПЕХ] Вариант Б (text, true) СРАБОТАЛ!");
                        }
                    }
                } catch (SQLException e2) {
                    System.out.println("-> [ОТКАЗ] Вариант Б (text, true) мимо: " + e2.getMessage().trim());

                    // Пробуем Вариант В
                    try (PreparedStatement stmt = conn.prepareStatement(sqlOptionВ)) {
                        stmt.setString(1, cleanMolfile);
                        try (ResultSet rs = stmt.executeQuery()) {
                            if (rs.next()) {
                                System.out.println("-> [УСПЕХ] Вариант В (mol_from_text) СРАБОТАЛ!");
                            }
                        }
                    } catch (SQLException e3) {
                        System.out.println("-> [ОТКАЗ] Вариант В (mol_from_text) мимо: " + e3.getMessage().trim());
                    }
                }
            }
            try (PreparedStatement stmt = conn.prepareStatement(targetedSql)) {
                stmt.setString(1, cleanMolfile);
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        Object res = rs.getObject(1);
                        System.out.println("-> Success! Cast Result: " + (res != null ? "Valid Molecule Object" : "NULL"));
                    }
                }

                java.sql.SQLWarning warning = stmt.getWarnings();
                if (warning != null) {
                    System.out.println("\n[POSTGRES WARNINGS]:");
                    while (warning != null) {
                        System.out.println("Message: " + warning.getMessage());
                        warning = warning.getNextWarning();
                    }
                }
            } catch (SQLException ex) {
                System.out.println("[DB EXECUTION FAILED] Error message: " + ex.getMessage());
            }

            // === ИСПРАВЛЕНИЕ ТУТ: Используем mol_from_ctab вместо ?::mol ===
            String testSql = "SELECT mol_from_ctab(?::text);";
            try (PreparedStatement stmt = conn.prepareStatement(testSql)) {
                stmt.setString(1, cleanMolfile);
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        Object res = rs.getObject(1);
                        System.out.println("-> Cast Result: " + (res != null ? "Valid Object" : "NULL"));
                    }
                }

                // Проверяем, насыпал ли Postgres нам инфы в Warnings
                java.sql.SQLWarning warning = stmt.getWarnings();
                if (warning != null) {
                    System.out.println("\n[POSTGRES WARNINGS]:");
                    while (warning != null) {
                        System.out.println("Message: " + warning.getMessage());
                        warning = warning.getNextWarning();
                    }
                } else {
                    System.out.println("\n[INFO] No explicit SQLWarnings returned to client.");
                }
            }

            // --- ШАГ 2: Вывод структуры для проверки смещения колонок ---
            System.out.println("\n--- GEOMETRY BLOCK CHECK ---");
            String[] lines = cleanMolfile.split("\n");
            int atomCount = 0;
            boolean bondPrinted = false;

            for (String line : lines) {
                // Выводим первые 2 строчки атомов для сверки таблицы атомов
                if (line.contains(" O ") || line.contains(" C ")) {
                    atomCount++;
                    if (atomCount <= 2) {
                        System.out.println("Atom Line: \"" + line + "\" (Length: " + line.length() + ")");
                        System.out.println("Ruler:     123456789012345678901234567890123456789012345678901234567890");
                    }
                }

                // Ищем и выводим первую строчку связи (Bond Line)
                String trimmed = line.trim();
                if (!bondPrinted && trimmed.length() > 0 && Character.isDigit(trimmed.charAt(0))) {
                    // Строка связи в V2000 состоит из чисел и обычно не содержит символов элементов
                    if (!line.contains("O") && !line.contains("C") && !line.contains("V2000")) {
                        System.out.println("Bond Line: \"" + line + "\" (Length: " + line.length() + ")");
                        System.out.println("Ruler:     123456789012345678901234567890123456789012345678901234567890");
                        bondPrinted = true;
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}