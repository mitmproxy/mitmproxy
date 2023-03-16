export GPG_TTY=$(tty)
echo "-----BEGIN PGP PRIVATE KEY BLOCK-----" >> private-key.asc
echo "" >> private-key.asc
echo "$GPG_PRIVATE_KEY" >> private-key.asc
echo "" >> private-key.asc
echo "-----END PGP PRIVATE KEY BLOCK-----" >> private-key.asc
gpg --import --batch private-key.asc
gpg-connect-agent 'getinfo version' /bye
gpg --pinentry-mode loopback --passphrase=$GPG_PASSPHRASE --export-secret-key $GPG_PUBLIC_KEY_SIGN > /tmp/secring.gpg

cd java && chmod +x ./gradlew;

echo "tmp: $OSSRH_JIRA_USERNAME"

./gradlew --project-prop "ossrhUsername=${OSSRH_JIRA_USERNAME}" --project-prop "ossrhPassword=${OSSRH_JIRA_PASSWORD}" --project-prop "signing.keyId=${GPG_PUBLIC_KEY_SIGN}" --project-prop "signing.password=${GPG_PASSPHRASE}" --project-prop "signing.secretKeyRingFile=/tmp/secring.gpg" --project-prop "sign=true" build publishPubToSonatypePublicationToMavenRepository --info; cd ../;

rm private-key.asc
